"""Red's attack packages fly in 2 or 3 grouped waves (§69, 2026-11-22).

Locks the wave math (even spacing up to just before the mission end, suppression
first, every package at or after its earliest arrival, the unreachable package
left alone) and the scheduler wiring (red only, ASAP and support untouched).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest

import game.commander.missionscheduler as ms
from game.ato.flighttype import FlightType
from game.commander.missionscheduler import (
    WAVE_JITTER,
    WAVE_SUPPRESSION_LEAD,
    attack_wave_tots,
)

T0 = datetime(2005, 4, 26, 23, 0)
END = T0 + timedelta(minutes=60)


def _tot(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def _wave_of(tot: datetime, waves: list[datetime]) -> int:
    for index, wave in enumerate(waves):
        if wave <= tot <= wave + WAVE_SUPPRESSION_LEAD + WAVE_JITTER:
            return index
    raise AssertionError(f"{tot} is in no wave of {waves}")


def test_waves_run_from_the_first_arrival_to_just_before_the_end() -> None:
    entries = [(i, _tot(34), False) for i in range(6)]
    tots = attack_wave_tots(entries, END, random.Random(1))
    waves = [_tot(34), _tot(45.5), _tot(57)]
    assert sorted({_wave_of(t, waves) for t in tots.values()}) == [0, 1, 2]
    assert all(t <= END for t in tots.values())


def test_every_package_arrives_no_earlier_than_it_can() -> None:
    entries = [(0, _tot(34), False), (1, _tot(40), False), (2, _tot(52), True)]
    entries += [(3, _tot(36), True), (4, _tot(55), False)]
    for seed in range(20):
        tots = attack_wave_tots(entries, END, random.Random(seed))
        for key, earliest, _ in entries:
            assert tots[key] >= earliest


def test_waves_are_balanced() -> None:
    entries = [(i, _tot(30), False) for i in range(9)]
    tots = attack_wave_tots(entries, END, random.Random(3))
    waves = [_tot(30), _tot(43.5), _tot(57)]
    counts = [0, 0, 0]
    for tot in tots.values():
        counts[_wave_of(tot, waves)] += 1
    assert counts == [3, 3, 3]


def test_suppression_leads_its_wave() -> None:
    # Three packages make two waves; the first two can make only the last.
    entries = [(0, _tot(56), True), (1, _tot(56), False), (2, _tot(30), False)]
    tots = attack_wave_tots(entries, END, random.Random(0))
    assert tots[0] < tots[1]
    assert tots[1] - tots[0] >= WAVE_SUPPRESSION_LEAD - WAVE_JITTER


def test_a_package_that_makes_no_wave_keeps_its_own_time() -> None:
    entries = [(0, _tot(30), False), (1, _tot(32), False), (2, _tot(70), False)]
    tots = attack_wave_tots(entries, END, random.Random(0))
    assert 2 not in tots
    assert set(tots) == {0, 1}


def test_one_package_or_no_room_changes_nothing() -> None:
    assert attack_wave_tots([(0, _tot(30), False)], END, random.Random(0)) == {}
    late = [(0, _tot(58), False), (1, _tot(59), False)]
    assert attack_wave_tots(late, END, random.Random(0)) == {}


def test_a_short_gap_makes_fewer_waves() -> None:
    entries = [(i, _tot(50), False) for i in range(6)]
    tots = attack_wave_tots(entries, END, random.Random(0))
    # 7 minutes of room holds two waves 5+ minutes apart, never three.
    waves = [_tot(50), _tot(57)]
    assert {_wave_of(t, waves) for t in tots.values()} == {0, 1}


# --- the scheduler wiring ---


def _package(task: FlightType, asap: bool = False) -> Any:
    return SimpleNamespace(
        primary_task=task,
        time_over_target=_tot(0),
        has_players=False,
        auto_asap=asap,
    )


def _waves(packages: list[Any], monkeypatch: pytest.MonkeyPatch) -> None:
    estimator = SimpleNamespace(earliest_tot=lambda now: _tot(30))
    monkeypatch.setattr(ms, "TotEstimator", lambda package: estimator)
    coalition = SimpleNamespace(ato=SimpleNamespace(packages=packages))
    scheduler = ms.MissionScheduler(cast(Any, coalition), timedelta(hours=1))
    scheduler._time_red_attack_waves(T0)


def test_attack_packages_are_waved_and_support_is_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    strikes = [_package(FlightType.STRIKE) for _ in range(3)]
    dead = _package(FlightType.DEAD)
    asap_cas = _package(FlightType.CAS, asap=True)
    csar = _package(FlightType.CSAR)
    _waves([*strikes, dead, asap_cas, csar], monkeypatch)
    for package in [*strikes, dead]:
        assert package.time_over_target >= _tot(30)
    assert asap_cas.time_over_target == _tot(0)
    assert csar.time_over_target == _tot(0)


def test_blue_is_never_waved() -> None:
    import inspect

    source = inspect.getsource(ms.MissionScheduler.schedule_missions)
    assert "if not self.coalition.player.is_blue:" in source
    assert "self._time_red_attack_waves(now)" in source
