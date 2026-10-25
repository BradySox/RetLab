"""Tornado presets follow the stock DCS fits and stay armed in period (2026-10-24).

Fulda Gap 1985 flew the GR4 with tanks and pods only: its bomb fits leaned on the
1999 Litening pod, and dropping the pod took the laser bombs with it.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from dcs import lua
from dcs.payloads import PayloadDirectories
from dcs.unittype import FlyingType

from game import persistency
from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.dcs.aircrafttype import AircraftType

PAYLOADS_DIR = Path(__file__).parents[2] / "resources" / "customized_payloads"
GBU_16 = "{0D33DDAE-524F-4A4E-B5B8-621754FE3ADE}"
BL_755 = "{08164777-5E9C-4B08-B48E-5AA7AFB246E2}"
MK_82 = "{BCE4E030-38E9-423E-98ED-24BE3DA87C32}"
ALARM = "{E6747967-B1F0-4C77-977B-AB2E6EB0C102}"
LITENING = "{A111396E-D3E8-4b9c-8AC9-2432489304D5}"
FACTION = SimpleNamespace(weapons_introduction_year_overrides={})


@pytest.fixture(autouse=True, scope="module")
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


@pytest.fixture(autouse=True)
def payload_dirs() -> None:
    PayloadDirectories.set_fallback(PAYLOADS_DIR)
    FlyingType._payload_cache = None  # type: ignore[assignment]


def _fits(aircraft: str) -> dict[str, dict[int, str]]:
    text = (PAYLOADS_DIR / f"{aircraft}.lua").read_text(encoding="utf-8")
    payloads = lua.loads(text)["unitPayloads"]
    return {
        p["name"]: {s["num"]: s["CLSID"] for s in p["pylons"].values()}
        for p in payloads["payloads"].values()
    }


@pytest.mark.parametrize(
    "aircraft,name,bomb,stations",
    [
        ("Tornado GR4", "Retribution Strike", GBU_16, {4, 9}),
        ("Tornado GR4", "Retribution DEAD", GBU_16, {4, 9}),
        ("Tornado GR4", "Retribution CAS", BL_755, {5, 6, 7, 8}),
        ("Tornado GR4", "Retribution BAI", BL_755, {5, 6, 7, 8}),
        ("Tornado GR4", "Retribution OCA/Aircraft", BL_755, {5, 6, 7, 8}),
        ("Tornado IDS", "Retribution Strike", GBU_16, {4, 9}),
        ("Tornado IDS", "Retribution DEAD", GBU_16, {4, 9}),
        ("Tornado IDS", "Retribution CAS", MK_82, {5, 6, 7, 8}),
    ],
)
def test_bomb_fits_are_the_stock_dcs_fits(
    aircraft: str, name: str, bomb: str, stations: set[int]
) -> None:
    fit = _fits(aircraft)[name]
    assert {n for n, clsid in fit.items() if clsid == bomb} == stations


def test_no_fit_carries_the_litening_pod() -> None:
    for aircraft in ("Tornado GR4", "Tornado IDS"):
        assert [n for n, f in _fits(aircraft).items() if LITENING in f.values()] == []


def test_every_store_fits_its_station() -> None:
    # The old IDS Strike fit hung Mk-82s on stations 4 and 9, which DCS does not allow.
    for aircraft in ("Tornado GR4", "Tornado IDS"):
        unit = AircraftType.named(aircraft)
        for name, fit in _fits(aircraft).items():
            assert Loadout.pylons_allow(unit, fit.items()), (aircraft, name)


@pytest.mark.parametrize("aircraft", ["Tornado GR4", "Tornado IDS"])
def test_the_tornado_has_its_own_laser_designator(aircraft: str) -> None:
    # laserEquipment.laserDesignator in the DCS unit data.
    data = yaml.safe_load(
        Path(f"resources/units/aircraft/{aircraft}.yaml").read_text(encoding="utf-8")
    )
    assert data["has_built_in_target_pod"] is True


@pytest.mark.parametrize("year", [1985, 1991])
@pytest.mark.parametrize("aircraft", ["Tornado GR4", "Tornado IDS"])
@pytest.mark.parametrize(
    "task",
    [
        FlightType.STRIKE,
        FlightType.DEAD,
        FlightType.CAS,
        FlightType.BAI,
        FlightType.OCA_AIRCRAFT,
        FlightType.OCA_RUNWAY,
    ],
    ids=lambda t: t.value,
)
def test_bomb_fits_stay_armed_in_period(
    aircraft: str, task: FlightType, year: int
) -> None:
    unit = AircraftType.named(aircraft)
    fit = Loadout.default_for_task_and_aircraft(task, unit.dcs_unit_type)
    dated = fit.degrade_for_date(unit, datetime.date(year, 6, 1), FACTION)  # type: ignore[arg-type]
    bombs = {GBU_16, BL_755, MK_82}
    assert any(w is not None and w.clsid in bombs for w in dated.pylons.values()), (
        aircraft,
        task.value,
        year,
        fit.name,
    )


def test_gr4_sead_carries_four_alarms() -> None:
    fits = _fits("Tornado GR4")
    for name in ("Retribution SEAD", "Retribution SEAD Escort"):
        assert {n for n, c in fits[name].items() if c == ALARM} == {3, 4, 9, 10}
