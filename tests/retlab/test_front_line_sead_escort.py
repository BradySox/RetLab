"""The Sidearm Harrier escorts the front line, not the deep packages.

Test 37 (2026-09-21, Long Road to H3): four AV-8B SEAD escorts went out on deep
packages, fired no Sidearm between them, and one pair died with the Armed Recon
package it covered to an SA-11 whose range the Sidearm cannot approach. The DM's
call: the Harrier is the escort for helicopters and A-10s at the front. Front-line
CAS asked only for a SEAD Sweep, which the Harrier cannot fly, so it never got
that job. With ``front_line_sead_escort`` on, CAS also asks for a SEAD Escort, the
flagged airframe is kept to front-line and helicopter-led packages, and it goes
first there.
"""

from types import SimpleNamespace
from typing import Any

import pytest

from game import persistency
from game.ato.flighttype import FlightType
from game.commander.missionproposals import EscortType
from game.dcs.aircrafttype import AircraftType
from game.settings.plannersuite import PLANNER_SUITE_VALUES
from game.squadrons.squadron import Squadron
from game.theater import FrontLine

HARRIER = "AV-8B Harrier II Night Attack"


@pytest.fixture(autouse=True, scope="module")
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


def test_only_the_harrier_is_marked_front_line_only() -> None:
    assert AircraftType.named(HARRIER).sead_escort_front_line_only
    for variant in (
        "F/A-18C Hornet (Lot 20)",
        "F-16CM Fighting Falcon (Block 50)",
        "EA-18G Growler",
    ):
        assert not AircraftType.named(variant).sead_escort_front_line_only, variant


def test_the_gate_is_in_the_retlab_planner_suite() -> None:
    assert PLANNER_SUITE_VALUES["front_line_sead_escort"] == (False, True)


def _front_line() -> FrontLine:
    # Only its type matters to the rule; skip FrontLine's own constructor.
    return FrontLine.__new__(FrontLine)


def _assign(
    aircraft: AircraftType, location: Any, *, heli: bool, setting: bool
) -> bool:
    squadron = SimpleNamespace(
        location=SimpleNamespace(cptype=SimpleNamespace(name="AIRBASE")),
        aircraft=aircraft,
        can_auto_assign=lambda task: True,
        settings=SimpleNamespace(front_line_sead_escort=setting),
    )
    return Squadron.can_auto_assign_mission(
        squadron,  # type: ignore[arg-type]
        location,
        FlightType.SEAD_ESCORT,
        size=2,
        heli=heli,
        this_turn=False,
        ignore_range=True,
    )


def test_the_harrier_escorts_the_front_line_and_helicopters_only() -> None:
    harrier = AircraftType.named(HARRIER)
    deep = SimpleNamespace()
    assert _assign(harrier, _front_line(), heli=False, setting=True)
    # A helicopter-led package already takes only helos and LHA jets as formation
    # escorts; the Harrier stays eligible there wherever it flies.
    assert _assign(harrier, deep, heli=True, setting=True)
    assert not _assign(harrier, deep, heli=False, setting=True)


def test_with_the_gate_off_the_harrier_plans_like_upstream() -> None:
    assert _assign(
        AircraftType.named(HARRIER), SimpleNamespace(), heli=False, setting=False
    )


def test_a_harm_shooter_still_escorts_deep() -> None:
    hornet = AircraftType.named("F/A-18C Hornet (Lot 20)")
    assert _assign(hornet, SimpleNamespace(), heli=False, setting=True)


def _cas_tasks(setting: bool) -> list[tuple[FlightType, Any]]:
    from game.commander.tasks.primitive.cas import PlanCas

    settings = SimpleNamespace(
        fpa_2ship_weight=1,
        fpa_3ship_weight=0,
        fpa_4ship_weight=0,
        front_line_sead_escort=setting,
    )
    target = SimpleNamespace(
        coalition=SimpleNamespace(game=SimpleNamespace(settings=settings))
    )
    task = PlanCas(target=target)  # type: ignore[arg-type]
    task.propose_flights()
    return [(f.task, f.escort_type) for f in task.flights]


def test_cas_asks_for_a_sead_escort_ahead_of_the_sweep() -> None:
    tasks = _cas_tasks(True)
    kinds = [t for t, _ in tasks]
    assert (FlightType.SEAD_ESCORT, EscortType.Sead) in tasks
    # Ahead of the sweep, so single_sead_escort_flavour keeps the escort.
    assert kinds.index(FlightType.SEAD_ESCORT) < kinds.index(FlightType.SEAD_SWEEP)


def test_stock_cas_is_unchanged() -> None:
    kinds = [t for t, _ in _cas_tasks(False)]
    assert FlightType.SEAD_ESCORT not in kinds
    assert FlightType.SEAD_SWEEP in kinds


def _ranked(monkeypatch: pytest.MonkeyPatch, location: Any, setting: bool) -> list[str]:
    import game.squadrons.airwing as airwing_module
    from game.squadrons.airwing import AirWing

    def squadron(variant: str) -> SimpleNamespace:
        return SimpleNamespace(
            aircraft=AircraftType.named(variant),
            primary_task=FlightType.BAI,
            location=SimpleNamespace(distance_to=lambda _: 100_000.0),
            can_auto_assign_mission=lambda *args: True,
        )

    base = SimpleNamespace(
        captured="blue",
        squadrons=[squadron("F/A-18C Hornet (Lot 20)"), squadron(HARRIER)],
    )
    monkeypatch.setattr(
        airwing_module.ObjectiveDistanceCache,
        "get_closest_airfields",
        staticmethod(lambda _: SimpleNamespace(operational_airfields=[base])),
    )
    wing = SimpleNamespace(
        player="blue",
        settings=SimpleNamespace(
            front_line_sead_escort=setting, primary_task_distance_factor=75
        ),
        _tanker_serves_methods=lambda aircraft, methods: True,
    )
    ranked = AirWing.best_squadrons_for(
        wing, location, FlightType.SEAD_ESCORT, 2, False, True  # type: ignore[arg-type]
    )
    return [s.aircraft.variant_id for s in ranked]


def test_at_the_front_the_harrier_ranks_ahead_of_the_harm_shooters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ranked = _ranked(monkeypatch, _front_line(), setting=True)
    assert ranked[0] == HARRIER


def test_without_the_gate_the_ranking_is_upstreams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ranked = _ranked(monkeypatch, _front_line(), setting=False)
    assert ranked[0] == "F/A-18C Hornet (Lot 20)"


# Test 39 (2026-09-23, Graveyard of Empires): the CAS package proposed its SEAD
# escort but never got one. The escort was needed only inside a fixed SAM ring, and
# red's front-line Tunguskas are not TGOs, so no ring covered FLOT START/END.


def _ground(dcs_type: Any) -> Any:
    from game.dcs.groundunittype import GroundUnitType

    return next(GroundUnitType.for_dcs_type(dcs_type))


def test_radar_air_defense_is_read_from_the_unit_data() -> None:
    from dcs.vehicles import AirDefence, Armor

    from game.ground_forces.ai_ground_planner import has_radar_air_defense

    for radar in (
        AirDefence.x_2S6_Tunguska,
        AirDefence.Osa_9A33_ln,
        AirDefence.ZSU_23_4_Shilka,
        AirDefence.Gepard,
    ):
        assert has_radar_air_defense({_ground(radar): 1}), radar.id
    for no_radar in (
        AirDefence.Strela_10M3,
        AirDefence.M1097_Avenger,
        AirDefence.Ural_375_ZU_23,
        Armor.T_72B,
    ):
        assert not has_radar_air_defense({_ground(no_radar): 4}), no_radar.id
    assert not has_radar_air_defense({_ground(AirDefence.x_2S6_Tunguska): 0})


class _FakeFrontLine(FrontLine):
    def __init__(self, enemy_cp: Any) -> None:
        self.enemy_cp = enemy_cp

    def control_point_hostile_to(self, player: Any) -> Any:
        return self.enemy_cp


def _needed(
    monkeypatch: pytest.MonkeyPatch, armor: Any, *, setting: bool, front: bool = True
) -> dict[EscortType, bool]:
    import game.ground_forces.ai_ground_planner as planner_module
    from game.commander.packagefulfiller import PackageFulfiller

    monkeypatch.setattr(planner_module, "deployable_armor", lambda cp: armor)
    cas = SimpleNamespace(
        flight_type=FlightType.CAS,
        flight_plan=SimpleNamespace(escorted_waypoints=lambda: iter(())),
    )
    target = _FakeFrontLine(SimpleNamespace()) if front else SimpleNamespace()
    builder = SimpleNamespace(
        package=SimpleNamespace(flights=[cas], primary_flight=cas, target=target)
    )
    no_ring = SimpleNamespace(
        waypoints_threatened_by_aircraft=lambda waypoints: False,
        waypoints_threatened_by_radar_sam=lambda waypoints: False,
    )
    fulfiller = PackageFulfiller.__new__(PackageFulfiller)
    fulfiller.coalition = SimpleNamespace(  # type: ignore[assignment]
        player="blue",
        doctrine=SimpleNamespace(always_escort_strikes=False),
        opponent=SimpleNamespace(threat_zone=no_ring),
    )
    fulfiller.front_line_sead_escort = setting
    return PackageFulfiller.check_needed_escorts(fulfiller, builder)  # type: ignore[arg-type]


def test_radar_air_defense_at_the_front_needs_the_sead_escort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dcs.vehicles import AirDefence

    armor = {_ground(AirDefence.x_2S6_Tunguska): 2}
    needed = _needed(monkeypatch, armor, setting=True)
    assert needed[EscortType.Sead]
    # Sead only: the escort jammer stays on the fixed-SAM trigger.
    assert not needed[EscortType.Jammer]


def test_ir_sams_and_guns_at_the_front_do_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dcs.vehicles import AirDefence

    armor = {
        _ground(AirDefence.Strela_10M3): 2,
        _ground(AirDefence.Ural_375_ZU_23): 2,
    }
    assert not _needed(monkeypatch, armor, setting=True)[EscortType.Sead]


def test_with_the_gate_off_the_front_does_not_need_sead(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dcs.vehicles import AirDefence

    armor = {_ground(AirDefence.x_2S6_Tunguska): 2}
    assert not _needed(monkeypatch, armor, setting=False)[EscortType.Sead]


def test_a_package_away_from_the_front_is_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dcs.vehicles import AirDefence

    armor = {_ground(AirDefence.x_2S6_Tunguska): 2}
    needed = _needed(monkeypatch, armor, setting=True, front=False)
    assert not needed[EscortType.Sead]
