"""Run in-game-pass rows that need no DCS, against a real shipped campaign.

Each check builds a fresh game from a campaign yaml (`_campaign_game.build_game`),
drives the real planner, and compares what it produced with the row's pass line.
A unit test with fakes is not evidence here: the logic behind every row is already
unit-tested, and the row owes the real run.

    python tools/row_checks.py            # every check
    python tools/row_checks.py B188       # the named rows

A row that passes is graded `◇ AUTO-PASS` by hand, with the printed evidence.
Exit 1 when any check fails.
"""

from __future__ import annotations

import logging
import random
import sys
from typing import Any, Callable

from _campaign_game import build_game

Check = Callable[[], list[str]]

#: Has a carrier and an LHA steaming together, a land front and deep targets.
CARRIER_CAMPAIGN = "syria_TheLongRoadToH3"
#: Afghanistan owns the Stennis's hull channel (74X), the case B156 is about.
MAP_OWNED_TACAN_CAMPAIGN = "coin_enduring_resolve"


def _replan(game: Any) -> None:
    from game.sim import GameUpdateEvents

    random.seed(414)
    game.initialize_turn(GameUpdateEvents(), for_red=True, for_blue=True)


def _tasks(game: Any, coalition: str) -> list[str]:
    ato = getattr(game, coalition).ato
    return [p.primary_task.value for p in ato.packages if p.primary_task]


def check_b19() -> list[str]:
    """Weather-aware planning: a storm puts front-line attack behind the deep work."""
    from game.weather.weather import ClearSkies, Thunderstorm

    game = build_game(CARRIER_CAMPAIGN)
    conditions = game.conditions
    args = (
        game.theater.seasonal_conditions,
        conditions.start_time.date(),
        conditions.time_of_day,
    )
    front = {"CAS", "BAI", "Armed Recon"}
    plans: dict[tuple[str, bool], dict[str, list[str]]] = {}
    for name, weather in (("clear", ClearSkies(*args)), ("storm", Thunderstorm(*args))):
        for enabled in (False, True):
            conditions.weather = weather
            game.settings.weather_aware_planning = enabled
            _replan(game)
            plans[name, enabled] = {s: _tasks(game, s) for s in ("blue", "red")}

    stock = plans["clear", False]
    assert plans["clear", True] == stock, "a clear-sky plan changes with the setting"
    assert plans["storm", False] == stock, "a storm changes the plan with it off"
    stormy = plans["storm", True]
    evidence = []
    for side in ("blue", "red"):
        assert front & set(stock[side]), f"{side} plans no front-line attack when clear"
        assert stormy[side] != stock[side], f"the storm left {side}'s plan alone"
        seen_front = False
        for task in stormy[side]:
            seen_front = seen_front or task in front
            deep = task in {"Strike", "DEAD", "Anti-ship", "OCA/Runway", "OCA/Aircraft"}
            assert not (seen_front and deep), f"{side}: {task} planned after CAS or BAI"
        evidence.append(f"{side} clear or setting off: {stock[side]}")
        evidence.append(f"{side} thunderstorm, setting on: {stormy[side]}")
    return evidence


def _generate(game: Any) -> None:
    """Generate the turn's mission to a temp file, as Take Off does.

    Straight through ``MissionGenerator``: ``MissionSimulation.generate_miz`` would
    also drop a copy in the user's mission archive.
    """
    import tempfile
    from pathlib import Path

    from game.missiongenerator import MissionGenerator
    from game.sim.missionsimulation import MissionSimulation

    sim = MissionSimulation(game)
    sim.begin_simulation()
    with tempfile.TemporaryDirectory() as folder:
        MissionGenerator(game, sim.time).generate_miz(Path(folder) / "row_check.miz")


def check_b156() -> list[str]:
    """A carrier keeps its TACAN across generations where the map owns its hull channel."""
    from game.data.carrier_comms import CARRIER_COMMS_PLANS

    game = build_game(MAP_OWNED_TACAN_CAMPAIGN)
    boats = [cp for cp in game.theater.controlpoints if cp.is_fleet]
    runs = []
    for _ in range(3):
        _generate(game)
        runs.append({cp.name: str(cp.tacan) for cp in boats})
    assert runs[0] == runs[1] == runs[2], f"TACAN changed between generations: {runs}"
    displaced = []
    for cp in boats:
        for unit in (
            u for tgo in cp.ground_objects for g in tgo.groups for u in g.units
        ):
            kind = unit.unit_type.dcs_unit_type.id if unit.unit_type else None
            plan = CARRIER_COMMS_PLANS.get(kind) if kind else None
            if plan is not None and str(plan.tacan) != str(cp.tacan):
                displaced.append(
                    f"{cp.name}: hull channel {plan.tacan}, got {cp.tacan}"
                )
    assert displaced, "no boat here has a map-owned hull channel; the case is not shown"
    return [f"three generations, every boat the same: {runs[0]}", *displaced]


def check_b188() -> list[str]:
    """An LHA within 80 NM of a carrier gets no BARCAP; a lone LHA gets its own."""
    from game.utils import meters

    game = build_game(CARRIER_CAMPAIGN)
    blue = [cp for cp in game.theater.controlpoints if cp.captured.is_blue]
    carrier = next(cp for cp in blue if cp.is_carrier)
    lha = next(cp for cp in blue if cp.is_lha)

    def barcap_targets() -> list[str]:
        return [
            p.target.name
            for p in game.blue.ato.packages
            if p.primary_task and p.primary_task.value == "BARCAP"
        ]

    def gap() -> float:
        return meters(lha.position.distance_to_point(carrier.position)).nautical_miles

    near_gap, near = gap(), barcap_targets()
    assert near_gap < 80, f"{lha.name} starts {near_gap:.0f} NM from the carrier"
    assert carrier.name in near, f"no BARCAP on {carrier.name}"
    assert lha.name not in near, f"BARCAP on {lha.name} beside its carrier"

    # No shipped campaign sails a lone LHA, so this one is moved 150 NM off.
    heading = carrier.position.heading_between_point(lha.position)
    lha.position = carrier.position.point_from_heading(heading, 150 * 1852)
    _replan(game)
    far_gap, far = gap(), barcap_targets()
    assert lha.name in far, f"no BARCAP on {lha.name} at {far_gap:.0f} NM"
    return [
        f"{lha.name} {near_gap:.0f} NM from {carrier.name}: BARCAP on {near}",
        f"{lha.name} moved to {far_gap:.0f} NM: BARCAP on {far}",
    ]


CHECKS: dict[str, Check] = {
    "B19": check_b19,
    "B156": check_b156,
    "B188": check_b188,
}


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.disable(logging.CRITICAL)
    failed = False
    for row in argv or list(CHECKS):
        try:
            evidence = CHECKS[row]()
        except AssertionError as error:
            failed = True
            print(f"{row} FAIL: {error}")
            continue
        print(f"{row} PASS")
        for line in evidence:
            print(f"  {line}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
