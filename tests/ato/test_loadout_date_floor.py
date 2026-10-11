"""A date limit never disarms an airframe that has no weapon of the day at all."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from dcs import lua
from dcs.planes import B_52H, H_6J, Tu_142, Tu_95MS

from game import persistency
from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.data.weapons import Weapon
from game.dcs.aircrafttype import AircraftType

KH_555_BAY = "{CHAP_Kh555x6}"
KH_555 = "{Kh-555}"
KH_35 = "{C42EE4C3-355C-4B83-8B22-B39430B8F4AE}"
KD_20 = "DIS_DF4A_KD20"
DATA_LINK_POD = "DIS_AKG_DLPOD"
YJ_83K = "DIS_GDJ_YJ83K"
MK_84 = "{696CFFC4-0BDE-42A8-BE4B-0BE3D9DD723C}"
LITENING = "{A111396E-D3E8-4b9c-8AC9-2432489304D5}"
BAY_HARPOONS = "{46ACDCF8-5451-4E26-BDDB-E78D5830E93C}"

FACTION: Any = SimpleNamespace()


def _aircraft(dcs_unit_type: Any) -> Any:
    return SimpleNamespace(dcs_unit_type=dcs_unit_type, has_built_in_target_pod=False)


def _degraded(dcs_unit_type: Any, stores: dict[int, str], year: int) -> dict[int, str]:
    loadout = Loadout(
        "Test", {n: Weapon.with_clsid(c) for n, c in stores.items()}, None
    )
    result = loadout.degrade_for_date(
        _aircraft(dcs_unit_type), date(year, 6, 1), FACTION
    )
    return {n: w.clsid for n, w in result.pylons.items() if w is not None}


@pytest.mark.parametrize(
    ("dcs_unit_type", "stores", "year"),
    [
        # Red Tide (1988) and Northern Flank 1985: the Kh-555 is 2004 in the data.
        (Tu_95MS, {1: KH_555_BAY, **{n: KH_555 for n in range(2, 10)}}, 1988),
        (Tu_95MS, {1: KH_555_BAY, **{n: KH_555 for n in range(2, 10)}}, 1985),
        # Northern Flank 1985: the Kh-35 is 2003.
        (Tu_142, {1: KH_35}, 1985),
    ],
)
def test_a_bomber_with_nothing_older_to_carry_keeps_its_fit(
    dcs_unit_type: Any, stores: dict[int, str], year: int
) -> None:
    assert _degraded(dcs_unit_type, stores, year) == stores


def test_a_pod_left_behind_does_not_count_as_armed() -> None:
    # Desert Storm (1991): the H-6J's KD-20 is 2008; its data-link pod has no year.
    stores = {**{n: KD_20 for n in range(1, 7)}, 7: DATA_LINK_POD}
    assert _degraded(H_6J, stores, 1991) == stores


def test_a_fit_with_an_older_weapon_still_loses_the_newer_one() -> None:
    # 2009: the KD-20 (2008) is in service, the YJ-83K (2010) is not and nothing
    # older fits an H-6J wing. The KD-20 keeps the jet armed, so the YJ-83K goes.
    assert _degraded(H_6J, {1: KD_20, 2: YJ_83K}, 2009) == {1: KD_20}


def test_an_airframe_with_another_weapon_in_service_is_still_stripped() -> None:
    # 2009: nothing older than the YJ-83K (2010) fits, but the H-6J could carry the
    # KD-20 (2008). The rule is for airframes with no weapon of the day at all.
    assert _degraded(H_6J, {2: YJ_83K}, 2009) == {}


def test_a_kept_fit_does_not_keep_its_targeting_pod() -> None:
    # 1950 predates every bomb the B-52H data knows, and the 1999 Litening pod.
    stores = {1: MK_84, 3: MK_84, 4: LITENING}
    assert _degraded(B_52H, stores, 1950) == {1: MK_84, 3: MK_84}


def test_an_armed_fit_still_loses_a_pod_past_the_date() -> None:
    assert _degraded(B_52H, {1: MK_84, 4: LITENING}, 1990) == {1: MK_84}


def test_weapon_settings_survive_on_a_kept_fit() -> None:
    settings = {1: {"some_setting": 1}}
    loadout = Loadout(
        "Test", {1: Weapon.with_clsid(KH_35)}, None, pylon_settings=settings
    )
    result = loadout.degrade_for_date(_aircraft(Tu_142), date(1985, 6, 1), FACTION)
    assert result.pylon_settings == settings


def test_shipped_b52h_anti_ship_fit_fills_the_bay() -> None:
    # Flown 2026-10-11: the bay rack launches. Read from the repo file, because a
    # player's own saved payload overrides it by name.
    text = Path("resources/customized_payloads/B-52H.lua").read_text(encoding="utf-8")
    payloads = lua.loads(text)["unitPayloads"]["payloads"]
    anti_ship = next(
        p for p in payloads.values() if p["name"] == "Retribution Anti-ship"
    )
    by_station = {p["num"]: p["CLSID"] for p in anti_ship["pylons"].values()}
    assert by_station[2] == BAY_HARPOONS
    assert by_station[1] == "{HSAB_4x_AGM84D_L}"
    assert by_station[3] == "{HSAB_4x_AGM84D_R}"


@pytest.mark.parametrize(
    ("variant_id", "removed", "kept"),
    [
        # The Tu-160 carries only cruise missiles and has only the Pinpoint Strike
        # role, which cannot order Attack Group.
        (
            "Tu-160 Blackjack",
            [FlightType.BAI, FlightType.DEAD],
            [FlightType.STRIKE],
        ),
        # The H-6J's BAI and DEAD fits were KD-20 cruise missiles.
        (
            "H-6J Badger",
            [FlightType.BAI, FlightType.DEAD],
            [FlightType.STRIKE, FlightType.ANTISHIP, FlightType.OCA_RUNWAY],
        ),
    ],
)
def test_cruise_missile_bombers_are_not_tasked_against_groups(
    variant_id: str,
    removed: list[FlightType],
    kept: list[FlightType],
    tmp_path: Path,
) -> None:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16889)
    aircraft = AircraftType.named(variant_id)
    for task in removed:
        assert not aircraft.capable_of(task), task
    for task in kept:
        assert aircraft.capable_of(task), task
