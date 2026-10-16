"""Coordinated TOT for hand-planned packages (§114).

Locks the window a Coordinated strike waits for (the §69 window), the ASAP
fall-backs and their warnings, the recon fog on what the warning may name, and
the Take Off pass that times suppression packages before the strikes behind them.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, Iterator, cast

import pytest
from dcs.mapping import Point
from dcs.terrain import Caucasus

from game.ato.flighttype import FlightType
from game.ato.package import Package
from game.commander import coordinatedtot
from game.commander.coordinatedtot import (
    apply_tot_mode,
    plan_coordinated_tot,
    retime_coordinated_packages,
)
from game.theater.player import Player
from game.utils import meters

T0 = datetime(2005, 4, 26, 23, 0)
LENGTH = timedelta(hours=1)
_TERRAIN = Caucasus()
SAM_POS = Point(0, 0, _TERRAIN)
IN_RING = Point(10_000, 0, _TERRAIN)
OUT_OF_RING = Point(100_000, 0, _TERRAIN)


def _tot(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


class FakeSam:
    has_live_radar_sam = True

    def __init__(self, name: str = "PIGLET", known: bool = True) -> None:
        self.name = name
        self.position = SAM_POS
        self.known = known

    def max_threat_range(self) -> Any:
        return meters(46_300)  # ~25 NM

    def known_for(self, viewer: Any) -> bool:
        return self.known

    def is_friendly(self, player: Any) -> bool:
        return False

    def is_dead(self) -> bool:
        return False


@pytest.fixture(autouse=True)
def fakes(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(coordinatedtot, "IadsGroundObject", FakeSam)
    monkeypatch.setattr(coordinatedtot, "TheaterGroundObject", FakeSam)
    monkeypatch.setattr(
        coordinatedtot,
        "TotEstimator",
        lambda package: SimpleNamespace(earliest_tot=lambda now: package.earliest),
    )
    yield


def _coalition(*sams: FakeSam, neutral: bool = False) -> Any:
    cp = SimpleNamespace(
        ground_objects=list(sams), captured=SimpleNamespace(is_neutral=neutral)
    )
    return SimpleNamespace(
        player=Player.BLUE,
        game=SimpleNamespace(theater=SimpleNamespace(controlpoints=[cp])),
    )


def _package(
    coalition: Any,
    task: FlightType,
    target: Any,
    earliest: datetime,
    tot: datetime | None = None,
    extra: tuple[FlightType, ...] = (),
) -> Any:
    flights = [
        SimpleNamespace(flight_type=t, coalition=coalition) for t in (task, *extra)
    ]
    package = SimpleNamespace(
        flights=flights,
        primary_task=task,
        target=target,
        earliest=earliest,
        time_over_target=tot if tot is not None else earliest,
        auto_coordinated=True,
        auto_asap=False,
        all_flights_waiting_for_start=lambda: True,
    )
    package.set_tot_asap = lambda now: setattr(
        package, "time_over_target", package.earliest
    )
    return package


def _target(position: Point = IN_RING) -> Any:
    return SimpleNamespace(name="Factory", position=position)


def _plan(package: Any, packages: list[Any]) -> coordinatedtot.CoordinatedTot:
    return plan_coordinated_tot(package, packages, T0, LENGTH)


def test_strike_waits_for_the_sead_on_the_sam_covering_it() -> None:
    sam = FakeSam()
    coalition = _coalition(sam)
    sead = _package(coalition, FlightType.SEAD, sam, _tot(20))
    strike = _package(coalition, FlightType.STRIKE, _target(), _tot(10))
    plan = _plan(strike, [sead, strike])
    assert plan.tot == _tot(22)
    assert plan.behind == [sead]
    assert plan.warnings == []


def test_strike_already_in_the_window_flies_asap() -> None:
    sam = FakeSam()
    coalition = _coalition(sam)
    sead = _package(coalition, FlightType.DEAD, sam, _tot(20))
    strike = _package(coalition, FlightType.BAI, _target(), _tot(25))
    plan = _plan(strike, [sead, strike])
    assert plan.tot == _tot(25)
    assert plan.behind == [sead]


def test_no_sead_planned_flies_asap_and_names_the_sam() -> None:
    coalition = _coalition(FakeSam("PIGLET"))
    strike = _package(coalition, FlightType.STRIKE, _target(), _tot(10))
    plan = _plan(strike, [strike])
    assert plan.tot == _tot(10)
    assert len(plan.warnings) == 1
    assert "PIGLET" in plan.warnings[0]


def test_a_sam_hidden_by_the_fog_is_never_named() -> None:
    coalition = _coalition(FakeSam(known=False))
    strike = _package(coalition, FlightType.STRIKE, _target(), _tot(10))
    assert _plan(strike, [strike]).warnings == []


def test_a_neutral_sam_is_not_a_threat_to_cover() -> None:
    coalition = _coalition(FakeSam(), neutral=True)
    strike = _package(coalition, FlightType.STRIKE, _target(), _tot(10))
    assert _plan(strike, [strike]).warnings == []


def test_a_target_outside_every_ring_needs_no_cover() -> None:
    coalition = _coalition(FakeSam())
    strike = _package(coalition, FlightType.STRIKE, _target(OUT_OF_RING), _tot(10))
    plan = _plan(strike, [strike])
    assert (plan.tot, plan.warnings) == (_tot(10), [])


def test_a_package_with_its_own_sead_escort_is_covered() -> None:
    coalition = _coalition(FakeSam())
    strike = _package(
        coalition,
        FlightType.STRIKE,
        _target(),
        _tot(10),
        extra=(FlightType.SEAD_ESCORT,),
    )
    assert _plan(strike, [strike]).warnings == []


def test_a_window_after_the_mission_ends_falls_back_to_asap() -> None:
    sam = FakeSam()
    coalition = _coalition(sam)
    sead = _package(coalition, FlightType.SEAD, sam, _tot(70))
    strike = _package(coalition, FlightType.STRIKE, _target(), _tot(10))
    plan = _plan(strike, [sead, strike])
    assert plan.tot == _tot(10)
    assert plan.behind == []
    assert "after the mission ends" in plan.warnings[0]


def test_a_window_it_cannot_reach_falls_back_to_asap() -> None:
    sam = FakeSam()
    coalition = _coalition(sam)
    sead = _package(coalition, FlightType.SEAD, sam, _tot(5))
    strike = _package(coalition, FlightType.STRIKE, _target(), _tot(40))
    plan = _plan(strike, [sead, strike])
    assert plan.tot == _tot(40)
    assert "closes at" in plan.warnings[0]


def test_a_suppression_package_itself_flies_asap() -> None:
    sam = FakeSam()
    coalition = _coalition(sam)
    other = _package(coalition, FlightType.DEAD, sam, _tot(30))
    sead = _package(coalition, FlightType.SEAD, sam, _tot(10))
    plan = _plan(sead, [other, sead])
    assert (plan.tot, plan.warnings) == (_tot(10), [])


def test_a_typed_tot_is_left_alone() -> None:
    coalition = _coalition()
    strike = _package(coalition, FlightType.STRIKE, _target(), _tot(10), _tot(33))
    strike.auto_coordinated = False
    assert apply_tot_mode(strike, [strike], T0, LENGTH) is None
    assert strike.time_over_target == _tot(33)


def test_asap_is_rerun_as_before() -> None:
    coalition = _coalition()
    strike = _package(coalition, FlightType.STRIKE, _target(), _tot(10), _tot(33))
    strike.auto_coordinated = False
    strike.auto_asap = True
    assert apply_tot_mode(strike, [strike], T0, LENGTH) is None
    assert strike.time_over_target == _tot(10)


def test_take_off_times_the_sead_before_the_strike_behind_it() -> None:
    sam = FakeSam()
    coalition = _coalition(sam)
    # Listed strike first, and the SEAD's saved TOT is stale: the strike must
    # wait for the SEAD's re-run TOT, not the old one.
    strike = _package(coalition, FlightType.STRIKE, _target(), _tot(10))
    sead = _package(coalition, FlightType.SEAD, sam, _tot(20), tot=_tot(50))
    game = SimpleNamespace(
        conditions=SimpleNamespace(start_time=T0),
        settings=SimpleNamespace(desired_player_mission_duration=LENGTH),
        blue=SimpleNamespace(ato=SimpleNamespace(packages=[strike, sead])),
        red=SimpleNamespace(ato=SimpleNamespace(packages=[])),
    )
    retime_coordinated_packages(cast(Any, game))
    assert sead.time_over_target == _tot(20)
    assert strike.time_over_target == _tot(22)


def test_an_old_save_reads_as_not_coordinated() -> None:
    package = Package.__new__(Package)
    package.__setstate__({"auto_asap": True})
    assert package.auto_coordinated is False
    assert package.auto_asap is True
