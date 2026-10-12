"""Escort jamming (§77) was removed 2026-10-12; old saves and campaigns must shed it."""

from __future__ import annotations

import io
import pickle
from pathlib import Path

import pytest
import yaml

from game.ato.flighttype import FlightType
from game.persistency import MigrationUnpickler
from game.settings import Settings
from game.settings.migration import migrate_legacy_settings


def test_the_task_is_gone() -> None:
    assert "ESCORT_JAMMER" not in FlightType.__members__
    assert "Escort Jammer" not in {task.value for task in FlightType}


def test_a_saved_escort_jammer_becomes_a_sead_escort() -> None:
    """A squadron task list, a flight and a campaign yaml all name the task by its
    value; the jammer flew the SEAD escort profile with the SEAD Escort fit."""
    assert FlightType("Escort Jammer") is FlightType.SEAD_ESCORT


def test_a_pickled_escort_jammer_loads_as_a_sead_escort() -> None:
    # Protocol 0 writes the value as text, so it can be swapped in place: this is
    # what a pre-removal save holds for the old member.
    data = pickle.dumps(FlightType.SEAD_ESCORT, protocol=0).replace(
        b"SEAD Escort", b"Escort Jammer"
    )
    assert b"Escort Jammer" in data

    assert MigrationUnpickler(io.BytesIO(data)).load() is FlightType.SEAD_ESCORT


def test_the_cap_setting_is_gone_and_an_old_save_sheds_its_key() -> None:
    assert not hasattr(Settings(), "max_escort_jammers")
    assert "max_escort_jammers" not in migrate_legacy_settings(
        {"max_escort_jammers": 4}
    )


def test_a_save_with_the_growler_plugin_ticked_sheds_its_keys() -> None:
    state = dict(Settings().__dict__)
    state["plugins"] = {**state["plugins"], "growler": True, "growler.debug": False}

    settings = Settings()
    settings.__setstate__(state)

    assert not [key for key in settings.plugins if key.split(".")[0] == "growler"]


@pytest.mark.parametrize("aircraft, sead_escort", [("EA-18G", 550), ("EA_6B", 460)])
def test_the_jammer_airframes_keep_a_job(aircraft: str, sead_escort: int) -> None:
    """Without the Escort Jammer lane both fly SEAD and SEAD Escort at upstream's weights."""
    tasks = yaml.safe_load(
        Path(f"resources/units/aircraft/{aircraft}.yaml").read_text(encoding="utf-8")
    )["tasks"]

    assert "Escort Jammer" not in tasks
    assert tasks["SEAD Escort"] == sead_escort
    assert "SEAD" in tasks
