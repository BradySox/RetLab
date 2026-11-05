from __future__ import annotations

from typing import Any, cast

from game.ato.airtaaskingorder import AirTaskingOrder
from game.ato.flighttype import FlightType
from game.ato.package import Package
from game.ato.replan import (
    detach_player_packages,
    reclaim_crews,
    restore_player_packages,
)
from game.theater.missiontarget import HomeBaseDefenseZone, MissionTarget


class _Squadron:
    def __init__(self, untasked: int, pilots: list[object]) -> None:
        self.untasked_aircraft = untasked
        self.available_pilots = list(pilots)


class _Roster:
    def __init__(self, pilots: list[object]) -> None:
        self.pilots = pilots

    def iter_pilots(self) -> Any:
        return iter(self.pilots)


class _Flight:
    def __init__(
        self, squadron: _Squadron, pilots: list[object], clients: int = 0
    ) -> None:
        self.squadron = squadron
        self.count = len(pilots)
        self.roster = _Roster(pilots)
        self.client_count = clients


class _Package:
    def __init__(
        self, task: FlightType, target: object, flights: list[_Flight]
    ) -> None:
        self.primary_task = task
        self.target = target
        self.flights = flights


class _Target:
    def __init__(self, name: str) -> None:
        self.name = name


def _ato(packages: list[_Package]) -> AirTaskingOrder:
    ato = AirTaskingOrder()
    ato.packages = cast(list[Package], list(packages))
    removed: list[Package] = []

    def remove_package(package: Package) -> None:
        removed.append(package)
        ato.packages.remove(package)

    ato.remove_package = remove_package  # type: ignore[method-assign]
    ato.removed = removed  # type: ignore[attr-defined]
    return ato


def test_only_packages_with_a_player_seat_are_lifted_out() -> None:
    squadron = _Squadron(0, [])
    mine = _Package(
        FlightType.STRIKE, _Target("Bridge"), [_Flight(squadron, ["a"], clients=1)]
    )
    ai = _Package(FlightType.STRIKE, _Target("Depot"), [_Flight(squadron, ["b"])])
    ato = _ato([mine, ai])

    kept = detach_player_packages(ato)

    assert kept == [mine]
    assert ato.packages == [ai]


def test_the_player_qra_alert_is_rebuilt_not_kept() -> None:
    squadron = _Squadron(0, [])
    zone = HomeBaseDefenseZone.__new__(HomeBaseDefenseZone)
    MissionTarget.__init__(zone, "QRA Alert Batumi", cast(Any, None))
    alert = _Package(FlightType.BARCAP, zone, [_Flight(squadron, ["a"], clients=1)])
    ato = _ato([alert])

    assert detach_player_packages(ato) == []
    assert ato.packages == [alert]


def test_kept_crews_are_booked_again_after_the_air_wing_reset() -> None:
    lead, wing, spare = object(), object(), object()
    squadron = _Squadron(untasked=6, pilots=[lead, wing, spare])
    package = _Package(
        FlightType.STRIKE,
        _Target("Bridge"),
        [_Flight(squadron, [lead, wing], clients=1)],
    )

    reclaim_crews(cast(list[Package], [package]))

    assert squadron.untasked_aircraft == 4
    assert squadron.available_pilots == [spare]


def test_restore_drops_one_new_duplicate_per_kept_package() -> None:
    squadron = _Squadron(0, [])
    bridge = _Target("Bridge")
    mine = _Package(FlightType.STRIKE, bridge, [_Flight(squadron, ["a"], clients=1)])
    dup = _Package(FlightType.STRIKE, bridge, [_Flight(squadron, ["b"])])
    other_task = _Package(FlightType.SEAD, bridge, [_Flight(squadron, ["c"])])
    second_dup = _Package(FlightType.STRIKE, bridge, [_Flight(squadron, ["d"])])
    ato = _ato([dup, other_task, second_dup])

    dropped = restore_player_packages(ato, cast(list[Package], [mine]))

    assert dropped == 1
    assert ato.removed == [dup]  # type: ignore[attr-defined]
    assert ato.packages == [other_task, second_dup, mine]
