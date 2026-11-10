"""Saved loadouts (features doc §128).

The §73 version wrote fits into DCS's UnitPayloads under the planner's preset
names, so a saved fit replaced the shipped preset for both coalitions in every
campaign and its old missiles could not step up. These pin the redesign.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import dcs.planes
import pytest

from game import persistency
from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon, Weapon
from game.dcs.aircrafttype import AircraftType
from game.retlab import saved_loadouts
from game.theater.player import Player


@pytest.fixture(scope="module", autouse=True)
def _persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


@pytest.fixture(autouse=True)
def _store(_persistency: None) -> Iterator[None]:
    persistency.saved_loadouts_path().unlink(missing_ok=True)
    saved_loadouts.reset_cache()
    yield
    saved_loadouts.reset_cache()


@pytest.fixture(scope="module")
def viper(_persistency: None) -> AircraftType:
    return next(AircraftType.for_dcs_type(dcs.planes.F_16C_50))


def _store_in_group(aircraft: AircraftType, group: str) -> tuple[int, Weapon]:
    """A station and a store of the named weapon group the station takes."""
    for pylon in Pylon.iter_pylons(aircraft):
        for weapon in sorted(pylon.allowed, key=lambda w: w.clsid):
            if weapon.weapon_group.name == group:
                return pylon.number, weapon
    raise AssertionError(f"no {group} station on {aircraft}")


def test_a_saved_fit_round_trips_under_its_own_name(viper: AircraftType) -> None:
    station, weapon = _store_in_group(viper, "AIM-120C")
    loadout = Loadout("Custom", {station: weapon}, date=None, is_custom=True)

    assert saved_loadouts.save(viper, "  Saved: Long range  ", loadout)
    saved_loadouts.reset_cache()

    assert saved_loadouts.names_for(viper) == ["Long range"]
    fit = saved_loadouts.load(viper, "Long range")
    assert fit is not None
    assert fit.loadout.name == "Saved: Long range"
    assert not fit.loadout.is_custom
    assert fit.loadout.pylons == {station: weapon}
    assert fit.notes == []


def test_a_saved_fit_never_takes_a_preset_name(viper: AircraftType) -> None:
    station, weapon = _store_in_group(viper, "AIM-120C")
    saved_loadouts.save(
        viper, "Retribution BARCAP", Loadout("x", {station: weapon}, None)
    )
    names = [loadout.name for loadout in saved_loadouts.all_for(viper)]
    assert names == ["Saved: Retribution BARCAP"]
    preset = Loadout.default_for_task_and_aircraft(
        FlightType.BARCAP, viper.dcs_unit_type
    )
    assert not saved_loadouts.is_saved_name(preset.name)


def test_an_old_sidewinder_steps_up(viper: AircraftType) -> None:
    station, nine_mike = _store_in_group(viper, "AIM-9M")
    saved_loadouts.save(viper, "Old", Loadout("x", {station: nine_mike}, None))

    fit = saved_loadouts.load(viper, "Old")
    assert fit is not None
    loaded = fit.loadout.pylons[station]
    assert loaded is not None
    assert loaded.weapon_group.name == "AIM-9X"


def test_a_store_the_pylon_cannot_carry_is_dropped(viper: AircraftType) -> None:
    station, weapon = _store_in_group(viper, "AIM-120C")
    saved_loadouts.save(viper, "Mod", Loadout("x", {station: weapon}, None))
    raw = saved_loadouts._load()[viper.dcs_unit_type.id]["Mod"]
    raw["pylons"]["99"] = {"clsid": "{NOT_A_STORE}", "settings": {}}

    fit = saved_loadouts.load(viper, "Mod")
    assert fit is not None
    assert fit.loadout.pylons == {station: weapon}
    assert fit.notes == ["Station 99: {NOT_A_STORE} cannot be loaded; left empty."]


def test_delete(viper: AircraftType) -> None:
    station, weapon = _store_in_group(viper, "AIM-120C")
    saved_loadouts.save(viper, "Gone", Loadout("x", {station: weapon}, None))
    assert saved_loadouts.delete(viper, "Gone")
    assert saved_loadouts.load(viper, "Gone") is None
    assert not saved_loadouts.delete(viper, "Gone")


def _flight(aircraft: AircraftType, player: Player, fits: dict[Any, str]) -> Any:
    squadron = SimpleNamespace(player=player, aircraft=aircraft, saved_loadouts=fits)
    return SimpleNamespace(
        squadron=squadron,
        flight_type=FlightType.BARCAP,
        unit_type=aircraft,
        package=SimpleNamespace(target=None),
    )


def _preset(aircraft: AircraftType) -> str:
    return Loadout.default_for_task_and_aircraft(
        FlightType.BARCAP, aircraft.dcs_unit_type
    ).name


def test_a_blue_squadron_fit_is_the_flight_default(viper: AircraftType) -> None:
    station, weapon = _store_in_group(viper, "AIM-120C")
    saved_loadouts.save(viper, "Sqn", Loadout("x", {station: weapon}, None))
    flight = _flight(viper, Player.BLUE, {FlightType.BARCAP: "Sqn"})

    assert Loadout.default_for(flight).name == "Saved: Sqn"


def test_red_never_takes_a_saved_fit(viper: AircraftType) -> None:
    station, weapon = _store_in_group(viper, "AIM-120C")
    saved_loadouts.save(viper, "Sqn", Loadout("x", {station: weapon}, None))
    flight = _flight(viper, Player.RED, {FlightType.BARCAP: "Sqn"})

    assert Loadout.default_for(flight).name == _preset(viper)


def test_a_deleted_squadron_fit_falls_back_to_the_preset(viper: AircraftType) -> None:
    flight = _flight(viper, Player.BLUE, {FlightType.BARCAP: "Never saved"})
    assert Loadout.default_for(flight).name == _preset(viper)


def test_old_squadrons_load_without_saved_fits() -> None:
    from game.squadrons.squadron import Squadron

    squadron = Squadron.__new__(Squadron)
    squadron.__setstate__({})
    assert squadron.saved_loadouts == {}
