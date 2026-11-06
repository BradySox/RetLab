"""F-4E stores that cannot share a wing (test 68, 2026-11-04).

Mk-83 TERs on the inboard pylons beside AIM-9Ls reached the mission; DCS kept the
AIM-9Ls and dropped the TERs, so the wingmen flew with 4 Mk-83 instead of 10.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pytest
from dcs import lua

from game.data.stationconflicts import (
    blocked_by,
    conflicting_rails,
    drop_conflicting_rails,
)

F4E = "F-4E-45MC"
MK83_TER = "{HB_F4E_MK-83_3x}"
MK82_SWA = "{HB_F4E_MK-82_2x_SWA}"
AIM_9L = "{AIM-9L}"
CLEAN = "<CLEAN>"


def _stores(fit: dict[int, str]) -> dict[int, Optional[SimpleNamespace]]:
    return {n: SimpleNamespace(clsid=c) for n, c in fit.items()}


# Test 68, CATFISH Strike as generated.
TEST_68 = {
    1: "{HB_F4E_MK-83_MER_2x}",
    2: AIM_9L,
    3: MK83_TER,
    4: AIM_9L,
    5: "{HB_F4E_AIM-7E-2}",
    6: "{HB_ALQ-131_ON_ADAPTER_IN_AERO7}",
    7: "{F4_SARGENT_TANK_600_GAL}",
    8: "{HB_F4E_AIM-7E-2}",
    9: "{HB_F4E_AIM-7E-2}",
    10: AIM_9L,
    11: MK83_TER,
    12: AIM_9L,
    13: "{HB_F4E_MK-83_MER_2x}",
    14: "{HB_ALE_40_30_60}",
}


def test_the_test_68_fit_conflicts_on_both_wings() -> None:
    assert conflicting_rails(F4E, _stores(TEST_68)) == [2, 4, 10, 12]


def test_mission_build_keeps_the_bombs_and_empties_the_rails() -> None:
    pylons = _stores(TEST_68)
    assert drop_conflicting_rails(F4E, pylons, "CATFISH") == [2, 4, 10, 12]
    assert {n: s.clsid for n, s in pylons.items() if s} == {
        n: c for n, c in TEST_68.items() if n not in (2, 4, 10, 12)
    }


def test_a_ter_picked_inboard_clears_that_wings_rails() -> None:
    pylons = _stores({2: AIM_9L, 3: MK83_TER, 4: AIM_9L, 10: AIM_9L})
    assert blocked_by(F4E, pylons, 3) == [2, 4]


def test_a_sidewinder_picked_on_a_rail_clears_a_blocking_inboard_store() -> None:
    pylons = _stores({2: AIM_9L, 3: MK83_TER})
    assert blocked_by(F4E, pylons, 2) == [3]


@pytest.mark.parametrize("inboard", [MK82_SWA, "{LAU68_FFAR_MK5HEAT}"])
def test_swa_loads_and_bare_lau68s_keep_the_rails(inboard: str) -> None:
    pylons = _stores({2: AIM_9L, 3: inboard, 4: AIM_9L})
    assert blocked_by(F4E, pylons, 3) == []
    assert blocked_by(F4E, pylons, 2) == []
    assert conflicting_rails(F4E, pylons) == []


def test_removing_the_inboard_pylon_takes_the_rails_with_it() -> None:
    pylons = _stores({3: CLEAN, 4: AIM_9L})
    assert blocked_by(F4E, pylons, 3) == [4]


def test_an_empty_rail_never_conflicts() -> None:
    pylons = _stores({2: CLEAN, 3: MK83_TER})
    assert conflicting_rails(F4E, pylons) == []
    assert blocked_by(F4E, pylons, 3) == []


def test_other_aircraft_have_no_rules() -> None:
    assert conflicting_rails("F-16C_50", _stores(TEST_68)) == []


def _f4e_presets() -> dict[str, dict[int, str]]:
    path = Path("resources/customized_payloads/F-4E-45MC.lua")
    payloads = lua.loads(path.read_text(encoding="utf-8"))["unitPayloads"]
    return {
        p["name"]: {s["num"]: s["CLSID"] for s in p["pylons"].values()}
        for p in payloads["payloads"].values()
    }


@pytest.mark.parametrize("name", sorted(_f4e_presets()))
def test_no_retlab_f4e_preset_breaks_the_rule(name: str) -> None:
    assert conflicting_rails(F4E, _stores(_f4e_presets()[name])) == []
