"""Heatblur F-4E presets that a 1985 campaign flies (Fulda Gap 1985, 2026-10-24).

Read from the repo file, because a player's own saved payload overrides it by name.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from dcs import lua

PAYLOADS = Path("resources/customized_payloads/F-4E-45MC.lua")
AIM_9P = "{9BFD8C90-F7AE-4e90-833B-BFD0CED0E536}"
ROCKEYE = {"{HB_F4E_ROCKEYE_2x_SWA}", "{HB_F4E_ROCKEYE_6x}"}
TANKS = {"{F4_SARGENT_TANK_370_GAL}", "{F4_SARGENT_TANK_370_GAL_R}"}


def _fits() -> dict[str, dict[int, str]]:
    payloads = lua.loads(PAYLOADS.read_text(encoding="utf-8"))["unitPayloads"]
    return {
        p["name"]: {s["num"]: s["CLSID"] for s in p["pylons"].values()}
        for p in payloads["payloads"].values()
    }


def test_no_fit_carries_the_aim_9p() -> None:
    assert [name for name, fit in _fits().items() if AIM_9P in fit.values()] == []


@pytest.mark.parametrize("name", ["Retribution BAI", "Retribution OCA/Aircraft"])
def test_cluster_fits_carry_rockeye_and_wing_tanks(name: str) -> None:
    # CBU-87 is 1986 and fell back to Mk-82 slicks; Rockeye is in service from 1968.
    fit = _fits()[name]
    assert {fit[3], fit[7], fit[11]} == ROCKEYE
    assert {fit[1], fit[13]} == TANKS


def test_sead_escort_keeps_the_sidewinders_sead_carries() -> None:
    fits = _fits()
    for station in (2, 4, 10, 12):
        assert fits["Retribution SEAD Escort"][station] == "{AIM-9M}"
        assert fits["Retribution SEAD"][station] == "{AIM-9M}"
