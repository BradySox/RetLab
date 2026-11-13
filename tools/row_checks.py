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


def check_b92() -> list[str]:
    """A marker outside every zone belongs to the base it sits next to (Desert Trident)."""
    import tempfile
    from pathlib import Path

    import dcs

    from game.missiongenerator import MissionGenerator
    from game.sim.missionsimulation import MissionSimulation
    from game.utils import meters

    game = build_game("operation_desert_trident")
    bases = {cp.name: cp for cp in game.theater.controlpoints}
    near, far = bases["King Abdullah II"], bases["Ben Gurion"]
    assert near.captured != far.captured, "the two bases are on one side"

    def nm(a: Any, b: Any) -> float:
        return meters(a.position.distance_to_point(b.position)).nautical_miles

    # The rule's own bounds: adopted within 25 km of a zoned base, and only when
    # the fallback owner is past 50 km. A marker outside them keeps its owner.
    adopt, stranded = 25 / 1.852, 50 / 1.852
    wrong = [
        t.name
        for t in far.ground_objects
        if nm(t, near) <= adopt and nm(t, far) > stranded
    ]
    assert not wrong, f"{far.name} still owns {wrong}, within 25 km of {near.name}"
    kept = [
        f"{t.name} {nm(t, near):.0f} NM from {near.name}"
        for t in far.ground_objects
        if nm(t, near) < nm(t, far)
    ]
    mine = {t.name for t in near.ground_objects}
    blue = [p.target.name for p in game.blue.ato.packages if p.target.name in mine]
    red = [p.target.name for p in game.red.ato.packages if p.target.name in mine]
    owner, enemy = (red, blue) if near.captured.is_red else (blue, red)
    assert not owner, f"{near.name}'s own side frags its objects: {owner}"

    sim = MissionSimulation(game)
    sim.begin_simulation()
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "row_check.miz"
        MissionGenerator(game, sim.time).generate_miz(path)
        mission = dcs.Mission()
        mission.load_file(str(path))
    side = "red" if near.captured.is_red else "blue"
    groups = {
        g.name
        for country in mission.coalition[side].countries.values()
        for g in country.vehicle_group + country.static_group + country.ship_group
    }
    spawned = [n for n in mine if any(n in g for g in groups)]
    assert spawned, f"none of {near.name}'s objects spawned on its side"
    return [
        f"{near.name} owns {len(mine)} objects, all within "
        f"{max(nm(t, near) for t in near.ground_objects):.0f} NM; none of "
        f"{far.name}'s is inside the adoption bound",
        f"the other side frags {len(enemy)} of them, its own side none",
        f"{len(spawned)} of them spawn in the mission under {side}",
        f"{far.name} keeps, outside the 25 km bound: {kept or 'none'}",
    ]


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


def _miz_payloads(
    game: Any, types: set[str]
) -> dict[str, set[tuple[tuple[int, str], ...]]]:
    """Each aircraft type's distinct pylon sets in the turn's generated mission."""
    import tempfile
    from pathlib import Path

    import dcs

    from game.missiongenerator import MissionGenerator
    from game.sim.missionsimulation import MissionSimulation

    sim = MissionSimulation(game)
    sim.begin_simulation()
    found: dict[str, set[tuple[tuple[int, str], ...]]] = {}
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "row_check.miz"
        MissionGenerator(game, sim.time).generate_miz(path)
        mission = dcs.Mission()
        mission.load_file(str(path))
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            for group in country.plane_group + country.helicopter_group:
                for unit in group.units:
                    if unit.type in types:
                        pylons = tuple(
                            sorted((int(n), s["CLSID"]) for n, s in unit.pylons.items())
                        )
                        found.setdefault(unit.type, set()).add(pylons)
    return found


def check_b282() -> list[str]:
    """The new stock AI jets fly their Retribution presets, as written to the mission."""
    from game.data.weapons import Weapon
    from game.dcs.aircrafttype import AircraftType

    # No shipped campaign fields all five, so real squadrons of one take each type.
    swaps = {
        "F/A-18C Hornet (Lot 20)": "F/A-18A",
        "Mirage-F1EQ": "Mirage-F1JA",
        "MiG-29A Fulcrum": "Mirage-F1JA",
        "JF-17 Thunder": "Mirage-F1JA",
        "MiG-21bis Fishbed-N": "Mirage-F1AZ",
        "Su-24M Fencer-D": "Mirage-F1CR",
        "Su-34 Fullback": "Mirage-F1CR",
        "Su-25 Frogfoot": "Su-25TM",
    }
    game = build_game("operation_desert_aladeen")
    by_id = {a.dcs_unit_type.id: a for a in AircraftType.iter_all()}
    for coalition in (game.blue, game.red):
        for squadron in coalition.air_wing.iter_squadrons():
            if squadron.aircraft.display_name in swaps:
                squadron.aircraft = by_id[swaps[squadron.aircraft.display_name]]
                # A squadron built for the new type would only auto-assign its tasks.
                squadron.auto_assignable_mission_types = {
                    task
                    for task in squadron.auto_assignable_mission_types
                    if squadron.aircraft.capable_of(task)
                }
    _replan(game)

    planned: dict[str, set[tuple[tuple[int, str], ...]]] = {}
    names: dict[str, set[str]] = {}
    for coalition in (game.blue, game.red):
        for flight in (f for p in coalition.ato.packages for f in p.flights):
            kind = flight.unit_type.dcs_unit_type.id
            if kind not in swaps.values():
                continue
            loadout = next(flight.iter_members()).loadout
            assert loadout.name.startswith(
                "Retribution "
            ), f"{kind} {flight.flight_type.value}: {loadout.name}"
            pylons = tuple(sorted((n, w.clsid) for n, w in loadout.pylons.items() if w))
            assert pylons, f"{kind} {flight.flight_type.value}: empty loadout"
            planned.setdefault(kind, set()).add(pylons)
            names.setdefault(kind, set()).add(
                f"{flight.flight_type.value}: {loadout.name}"
            )
    missing = set(swaps.values()) - set(planned)
    assert not missing, f"the planner fragged none of {sorted(missing)}"

    written = _miz_payloads(game, set(swaps.values()))
    for kind, sets in planned.items():
        clean = {
            tuple(p for p in s if p[1] != "<CLEAN>") for s in written.get(kind, set())
        }
        assert sets <= clean, f"{kind}: the mission does not carry the planned fit"
    for pylons in written["Mirage-F1JA"]:
        tips = {n for n, clsid in pylons if clsid == "{R550_Magic_1}"}
        assert {1, 7} <= tips, f"F1JA wingtips empty: {pylons}"
    for pylons in written["F/A-18A"]:
        for _, clsid in pylons:
            weapon = Weapon.with_clsid(clsid)
            label = weapon.name if weapon else clsid
            assert "FLIR" not in label and "AAS-38" not in label, f"F/A-18A: {label}"
    return [f"{kind}: {sorted(names[kind])}" for kind in sorted(names)] + [
        "F1JA: R550 Magic on stations 1 and 7 in every group",
        "F/A-18A: no FLIR pod on any station",
    ]


def check_b319() -> list[str]:
    """A player escort's route ends at its Escort Hold; nothing sits on the target."""
    from game.ato.flighttype import FlightType
    from game.utils import meters

    game = build_game(CARRIER_CAMPAIGN)
    evidence = []
    for package in game.blue.ato.packages:
        if package.primary_task not in (FlightType.DEAD, FlightType.STRIKE):
            continue
        primary = next(
            f for f in package.flights if f.flight_type == package.primary_task
        )
        for flight in package.flights:
            if flight.flight_type not in (FlightType.ESCORT, FlightType.SEAD_ESCORT):
                continue
            next(flight.iter_members()).pilot.player = True
            flight.recreate_flight_plan()
            route = list(flight.flight_plan.iter_waypoints())
            names = [w.name for w in route]
            label = f"{package.primary_task.value} {flight.flight_type.value}"
            hold = names.index("ESCORT HOLD")
            assert names[hold - 1] == "INGRESS", f"{label}: {names}"
            assert names[hold + 1] == "SPLIT", f"{label}: {names}"
            near = [
                w.name
                for w in route
                if meters(w.position.distance_to_point(package.target.position))
                < meters(1852 * 2)
            ]
            assert not near, f"{label}: {near} on the target"
            joins = [
                f.flight_plan.depart_time_for_waypoint(
                    next(w for w in f.flight_plan.iter_waypoints() if w.name == "JOIN")
                )
                for f in (flight, primary)
            ]
            assert joins[0] == joins[1], f"{label}: join {joins[0]} vs {joins[1]}"
            to_hold = meters(
                route[hold].position.distance_to_point(package.target.position)
            )
            evidence.append(
                f"{label}: {' > '.join(names[:hold + 2])}, hold "
                f"{to_hold.nautical_miles:.1f} NM off the target, join with the primary"
            )
    assert evidence, "no Strike or DEAD package carries an escort"
    return evidence


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
    "B92": check_b92,
    "B19": check_b19,
    "B156": check_b156,
    "B282": check_b282,
    "B319": check_b319,
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
