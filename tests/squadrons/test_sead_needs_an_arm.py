"""The planner does not send a jet on SEAD when the date took its last ARM.

Test 56 (2026-10-11, Iraq 2012): the JF-17's SEAD fit carries LD-10s, which the
weapon data dates to 2013. With weapon dates restricted both pairs were removed
and nothing replaced them, so a JF-17 pair flew SEAD escort with a jammer pod
and two PL-5. A fit that has no anti-radiation missile by design is left alone.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from dcs.payloads import PayloadDirectories
from dcs.unittype import FlyingType

from game import persistency
from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.data.weapons import WeaponType
from game.dcs.aircrafttype import AircraftType
from game.squadrons.squadron import Squadron

PAYLOADS_DIR = Path(__file__).parents[2] / "resources" / "customized_payloads"
SEAD_TASKS = [FlightType.SEAD, FlightType.SEAD_ESCORT, FlightType.SEAD_SWEEP]


@pytest.fixture(autouse=True, scope="module")
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


@pytest.fixture(autouse=True)
def payload_dirs() -> None:
    PayloadDirectories.set_fallback(PAYLOADS_DIR)
    FlyingType._payload_cache = None  # type: ignore[assignment]


def _squadron(variant: str, year: int, by_date: bool = True) -> Any:
    game = SimpleNamespace(
        date=datetime.date(year, 5, 16),
        settings=SimpleNamespace(
            max_mission_range_planes=500, max_mission_range_helicopters=200
        ),
    )
    squadron = SimpleNamespace(
        location=SimpleNamespace(cptype=SimpleNamespace(name="AIRBASE")),
        aircraft=AircraftType.named(variant),
        coalition=SimpleNamespace(game=game, faction=None),
        settings=SimpleNamespace(
            restrict_weapons_by_date=by_date, front_line_sead_escort=False
        ),
        can_auto_assign=lambda task: True,
    )
    squadron._date_strips_every_arm = lambda task: Squadron._date_strips_every_arm(
        squadron, task  # type: ignore[arg-type]
    )
    return squadron


def _assigns(squadron: Any, task: FlightType) -> bool:
    return Squadron.can_auto_assign_mission(
        squadron, SimpleNamespace(), task, 2, False, False, ignore_range=True  # type: ignore[arg-type]
    )


@pytest.mark.parametrize("task", SEAD_TASKS, ids=lambda t: t.value)
def test_a_jf17_is_not_sent_on_sead_before_its_arm_exists(task: FlightType) -> None:
    jf17 = AircraftType.named("JF-17 Thunder")
    fit = Loadout.default_for_task_and_aircraft(task, jf17.dcs_unit_type)
    assert fit.has_weapon_of_type(WeaponType.ARM)

    assert not _assigns(_squadron("JF-17 Thunder", 2012), task)
    assert _assigns(_squadron("JF-17 Thunder", 2013), task)


def test_the_rule_is_off_when_weapon_dates_are_not_restricted() -> None:
    squadron = _squadron("JF-17 Thunder", 2012, by_date=False)
    assert _assigns(squadron, FlightType.SEAD_ESCORT)


def test_other_tasks_are_untouched() -> None:
    squadron = _squadron("JF-17 Thunder", 2012)
    assert _assigns(squadron, FlightType.BARCAP)
    assert _assigns(squadron, FlightType.STRIKE)


def test_a_viper_keeps_sead_in_2012() -> None:
    squadron = _squadron("F-16CM Fighting Falcon (Block 50)", 2012)
    assert all(_assigns(squadron, task) for task in SEAD_TASKS)


def test_a_fit_with_no_arm_by_design_is_left_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decoys or Mavericks on a SEAD fit are a choice, not something the date took."""
    monkeypatch.setattr(
        Loadout,
        "default_for_task_and_aircraft",
        classmethod(lambda cls, task, dcs_type, target=None: Loadout.empty_loadout()),
    )
    assert _assigns(_squadron("JF-17 Thunder", 1990), FlightType.SEAD)


@pytest.mark.parametrize("task", SEAD_TASKS, ids=lambda t: t.value)
def test_a_tornado_gr4_flies_sead_only_once_alarm_exists(task: FlightType) -> None:
    # ALARM is dated 1990 and the GR4 carries no other ARM in DCS (Fulda Gap 1985).
    assert not _assigns(_squadron("Tornado GR4", 1985), task)
    assert _assigns(_squadron("Tornado GR4", 1991), task)
