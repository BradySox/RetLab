"""An anti-ship flight turns for home once it has no weapon left.

Test 55 (2026-10-11): four AI B-52Hs fired all their Harpoons from about 83 NM and
then flew the rest of the route, ending 9 NM from the Kuznetsov at 18,000 ft.
"""

from types import SimpleNamespace
from typing import Any

from dcs.task import OptRTBOnOutOfAmmo

from game.missiongenerator.aircraft.aircraftbehavior import AircraftBehavior


class _RecordingBehavior(AircraftBehavior):
    def __init__(self) -> None:  # do not call super
        self.recorded: dict[str, Any] = {}

    def configure_task(  # type: ignore[override]
        self, flight: Any, group: Any, task: Any, fallback_tasks: Any = None
    ) -> None:
        pass

    def configure_behavior(  # type: ignore[override]
        self, flight: Any, group: Any, **kwargs: Any
    ) -> None:
        self.recorded = kwargs


def test_anti_ship_flight_returns_when_out_of_weapons() -> None:
    behavior = _RecordingBehavior()
    behavior.configure_anti_ship(SimpleNamespace(), SimpleNamespace())  # type: ignore[arg-type]
    # All, not ASM: a flight sent with bombs only would count as out of missiles
    # at spawn and never attack. The gun is taken away, so All can be reached.
    assert behavior.recorded["rtb_winchester"] == OptRTBOnOutOfAmmo.Values.All
    assert behavior.recorded["mission_uses_gun"] is False
