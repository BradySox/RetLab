from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from game.debriefing import Debriefing
    from game.sim import MissionSimulation


#: How often (seconds) we check state.json. DCS' export hook rewrites the
#: file every second once the mission has ended, so a short interval keeps
#: end-of-mission detection responsive without burning CPU.
POLL_INTERVAL_SECONDS = 2


class DebriefingFilePoller:
    """One check of state.json per poll(); the caller schedules the polls.

    The UI calls poll() from a timer on its own thread. It used to run on a
    plain thread, and the debrief signals it emitted from there are the likely
    cause of the PySide crashes after mission end (features doc §8).
    """

    def __init__(
        self,
        callback: Callable[[Debriefing], None],
        mission_sim: MissionSimulation,
        state_path: Path = Path("state.json"),
    ) -> None:
        self.callback = callback
        self.mission_sim = mission_sim
        self.state_path = state_path
        # Treat any state.json newer than this mission's .miz as the current
        # mission's result; an older file is a stale leftover from a previous
        # mission and is ignored until DCS rewrites it.
        self.last_modified = mission_sim.miz_generated_at
        self._stopped = False
        logging.info(
            "Watching state.json for writes after mission launch (mtime > %s)",
            self.last_modified,
        )

    def stop(self) -> None:
        self._stopped = True

    def stopped(self) -> bool:
        return self._stopped

    def poll(self) -> None:
        if self._stopped:
            return
        try:
            if (
                os.path.isfile(self.state_path)
                and os.path.getmtime(self.state_path) > self.last_modified
            ):
                debriefing = self.mission_sim.debrief_current_state(self.state_path)
                self.callback(debriefing)
                self.last_modified = os.path.getmtime(self.state_path)
                if debriefing.state_data.mission_ended:
                    logging.info("Mission end detected; stopping poll")
                    self.stop()
        except (json.JSONDecodeError, OSError, ValueError, KeyError):
            logging.error(
                "Failed to read state.json (likely read while DCS was "
                "still writing it); will retry in %ss.",
                POLL_INTERVAL_SECONDS,
                exc_info=True,
            )
