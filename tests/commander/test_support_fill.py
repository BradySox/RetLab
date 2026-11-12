"""Fill support (§130): the package window's button that adds escort and SEAD.

It runs the planner's own route check on a hand-built package. These pin the
choices: 2-ships, one suppression flight, TARCAP for CAS, keep what fits, and a
SAM check that counts only sites on the player's map.
"""

from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace
from typing import Any, Iterable

import pytest

from game.ato.flighttype import FlightType
from game.commander import supportfill
from game.commander.missionproposals import EscortType
from game.commander.packagefulfiller import PackageFulfiller
from game.theater import fogofwar
from game.theater.player import Player


class FakePackage:
    def __init__(self, primary: FlightType) -> None:
        self.target = SimpleNamespace(name="target")
        self.auto_asap = False
        self.flights: list[Any] = [_flight(primary)]
        self.removed: list[Any] = []

    @property
    def primary_task(self) -> FlightType:
        return self.flights[0].flight_type

    def add_flight(self, flight: Any) -> None:
        self.flights.append(flight)

    def remove_flight(self, flight: Any) -> None:
        self.flights.remove(flight)
        self.removed.append(flight)


def _flight(task: FlightType, fails_plan: bool = False) -> Any:
    def recreate() -> None:
        if fails_plan:
            raise supportfill.PlanningError("no plan")

    return SimpleNamespace(
        flight_type=task,
        count=2,
        unit_type="F-16CM",
        recreate_flight_plan=recreate,
    )


def _install(
    monkeypatch: pytest.MonkeyPatch,
    *,
    a2a: bool,
    sead: bool,
    free: Iterable[FlightType],
    unplannable: Iterable[FlightType] = (),
) -> list[FlightType]:
    """Fakes the planner; returns the tasks the builder was asked for, in order."""
    asked: list[FlightType] = []
    free_set, bad = set(free), set(unplannable)

    class FakeFulfiller:
        def __init__(self, *args: Any, threat_zones: Any = None) -> None:
            self.threat_zones = threat_zones

        def check_needed_escorts(self, builder: Any) -> dict[EscortType, bool]:
            needed: dict[EscortType, bool] = defaultdict(bool)
            needed[EscortType.AirToAir] = a2a
            needed[EscortType.Sead] = sead
            return needed

    class FakeBuilder:
        def __init__(self, *args: Any) -> None:
            self.package: Any = None

        def plan_flight(self, plan: Any, ignore_range: bool) -> bool:
            assert not ignore_range
            assert plan.num_aircraft == 2
            asked.append(plan.task)
            if plan.task not in free_set:
                return False
            self.package.add_flight(_flight(plan.task, plan.task in bad))
            return True

    monkeypatch.setattr(supportfill, "PackageFulfiller", FakeFulfiller)
    monkeypatch.setattr(supportfill, "PackageBuilder", FakeBuilder)
    monkeypatch.setattr(
        supportfill.ObjectiveDistanceCache,
        "get_closest_airfields",
        staticmethod(lambda target: None),
    )
    return asked


def _fill(package: FakePackage, allows: Any = None) -> supportfill.SupportFillResult:
    coalition = SimpleNamespace(
        air_wing=None,
        laser_code_registry=None,
        player=Player.BLUE,
        doctrine=SimpleNamespace(allows=allows or (lambda task: True)),
    )
    game = SimpleNamespace(
        theater=None,
        db=SimpleNamespace(flights=None),
        settings=SimpleNamespace(default_start_type=None),
    )
    return supportfill.fill_package_support(
        game, coalition, package, threat_zones=object()  # type: ignore[arg-type]
    )


def _tasks(flights: Iterable[Any]) -> list[FlightType]:
    return [f.flight_type for f in flights]


def test_a_threatened_strike_gets_an_escort_and_one_sead_flight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(
        monkeypatch,
        a2a=True,
        sead=True,
        free={FlightType.ESCORT, FlightType.SEAD_ESCORT, FlightType.SEAD_SWEEP},
    )
    package = FakePackage(FlightType.STRIKE)
    result = _fill(package)
    assert _tasks(result.added) == [FlightType.ESCORT, FlightType.SEAD_ESCORT]
    assert _tasks(package.flights) == [
        FlightType.STRIKE,
        FlightType.ESCORT,
        FlightType.SEAD_ESCORT,
    ]
    assert not result.not_added


def test_an_unthreatened_route_gets_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = _install(monkeypatch, a2a=False, sead=False, free=set(FlightType))
    result = _fill(FakePackage(FlightType.STRIKE))
    assert not result.added and not asked


def test_cas_is_covered_by_tarcap(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, a2a=True, sead=False, free=set(FlightType))
    result = _fill(FakePackage(FlightType.CAS))
    assert _tasks(result.added) == [FlightType.TARCAP]


def test_sead_falls_back_to_a_sweep(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = _install(monkeypatch, a2a=False, sead=True, free={FlightType.SEAD_SWEEP})
    result = _fill(FakePackage(FlightType.STRIKE))
    assert asked == [FlightType.SEAD_ESCORT, FlightType.SEAD_SWEEP]
    assert _tasks(result.added) == [FlightType.SEAD_SWEEP]


def test_keeps_what_fits_and_says_what_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(monkeypatch, a2a=True, sead=True, free={FlightType.ESCORT})
    result = _fill(FakePackage(FlightType.STRIKE))
    assert _tasks(result.added) == [FlightType.ESCORT]
    assert result.not_added == ["No SEAD added: no free SEAD jets in range this turn."]
    assert "No SEAD added" in result.summary()


def test_cover_already_in_the_package_is_not_doubled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked = _install(monkeypatch, a2a=True, sead=True, free=set(FlightType))
    package = FakePackage(FlightType.STRIKE)
    package.flights.append(_flight(FlightType.ESCORT))
    package.flights.append(_flight(FlightType.SEAD))
    result = _fill(package)
    assert not result.added and not asked


def test_an_era_without_sead_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, a2a=False, sead=True, free=set(FlightType))
    result = _fill(
        FakePackage(FlightType.STRIKE),
        allows=lambda task: task not in supportfill.SEAD_COVER,
    )
    assert not result.added
    assert result.not_added == ["No SEAD added: this era's doctrine flies none."]


def test_a_flight_that_cannot_be_routed_is_handed_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(
        monkeypatch,
        a2a=False,
        sead=True,
        free={FlightType.SEAD_ESCORT, FlightType.SEAD_SWEEP},
        unplannable={FlightType.SEAD_ESCORT},
    )
    package = FakePackage(FlightType.STRIKE)
    result = _fill(package)
    assert _tasks(package.removed) == [FlightType.SEAD_ESCORT]
    assert _tasks(result.added) == [FlightType.SEAD_SWEEP]


def test_the_sam_check_uses_the_players_map_with_the_overview_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    def for_faction(game: Any, player: Player, viewer: Any = None) -> str:
        seen.update(player=player, viewer=viewer, revealed=fogofwar.fog_revealed())
        return "zones"

    monkeypatch.setattr(
        supportfill.ThreatZones, "for_faction", staticmethod(for_faction)
    )
    coalition = SimpleNamespace(
        game="game",
        player=Player.BLUE,
        opponent=SimpleNamespace(player=Player.RED),
    )
    fogofwar.set_fog_revealed(True)
    try:
        zones = supportfill.player_threat_zones(coalition)  # type: ignore[arg-type]
    finally:
        fogofwar.set_fog_revealed(False)
    assert zones == "zones"
    assert seen == {"player": Player.RED, "viewer": Player.BLUE, "revealed": False}


def test_the_fulfiller_takes_the_players_zones() -> None:
    settings = SimpleNamespace(
        auto_ato_player_missions_asap=False,
        default_start_type=None,
        single_sead_escort_flavour=False,
        front_line_sead_escort=False,
    )
    zones = object()
    fulfiller = PackageFulfiller(
        None, None, None, settings, threat_zones=zones  # type: ignore[arg-type]
    )
    assert fulfiller.threat_zones is zones
