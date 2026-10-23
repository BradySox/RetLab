"""The Shrike seeker head is matched to the target's radars without undoing a
hand-set value (features doc §8)."""

from __future__ import annotations

from typing import Any

import pytest

from game.ato.loadouts import Loadout
from game.data.weapons import Weapon

SHRIKE = "{LAU_34_AGM_45B}"
HEAD = "NFP_rfgu_type"
SA3 = ("p-19 s-125 sr", "snr s-125 tr")
SA2 = ("p-19 s-125 sr", "SNR_75V")


def _shrike() -> Weapon:
    weapon = Weapon.with_clsid(SHRIKE)
    assert weapon is not None
    return weapon


def test_matched_head_comes_with_the_full_table() -> None:
    settings = _shrike().settings_for_target(None, SA3)
    assert settings is not None
    assert settings[HEAD] == 9  # Mk 49 Mod 1
    # DCS reads an absent key as not fitted, so the rest are written too.
    assert settings["EAS_bypass_ctrl"] == 1
    assert settings["smoke_marker"] == 0


def test_fan_song_gets_its_own_head_before_the_flat_face_rule() -> None:
    settings = _shrike().settings_for_target(None, SA2)
    assert settings is not None
    assert settings[HEAD] == 5  # Mk 25


def test_an_unlisted_radar_gets_the_broad_head() -> None:
    settings = _shrike().settings_for_target(None, ("Hawk tr", "Hawk sr"))
    assert settings is not None
    assert settings[HEAD] == 10  # Mk 50


def test_a_hand_set_head_and_profile_survive() -> None:
    stored = {HEAD: 2, "EAS_bypass_ctrl": 0, "smoke_marker": 1}
    settings = _shrike().settings_for_target(stored, SA3)
    assert settings is not None
    assert settings[HEAD] == 2
    assert settings["EAS_bypass_ctrl"] == 0
    assert settings["smoke_marker"] == 1


def test_a_head_left_at_default_is_matched_with_the_profile_kept() -> None:
    stored = {HEAD: 1, "EAS_bypass_ctrl": 0}
    settings = _shrike().settings_for_target(stored, SA3)
    assert settings is not None
    assert settings[HEAD] == 9
    assert settings["EAS_bypass_ctrl"] == 0


def test_no_target_leaves_the_stored_settings_alone() -> None:
    stored = {HEAD: 3}
    assert _shrike().settings_for_target(stored, ()) is stored


def test_saving_the_matched_head_stores_it_as_automatic() -> None:
    weapon = _shrike()
    shown = weapon.settings_for_target(None, SA3)
    assert shown is not None
    saved = weapon.strip_target_settings(shown, SA3)
    assert saved[HEAD] == 1
    # Still follows the target once saved.
    again = weapon.settings_for_target(saved, SA2)
    assert again is not None and again[HEAD] == 5


def test_a_different_saved_head_is_kept_as_a_hand_pick() -> None:
    weapon = _shrike()
    saved = weapon.strip_target_settings({HEAD: 2, "EAS_bypass_ctrl": 1}, SA3)
    assert saved[HEAD] == 2


def test_loadout_applies_heads_per_pylon(monkeypatch: pytest.MonkeyPatch) -> None:
    weapon = _shrike()
    loadout = Loadout("test", {1: weapon, 2: weapon}, date=None)
    loadout.pylon_settings[2] = {HEAD: 4}
    monkeypatch.setattr(Loadout, "target_unit_ids", staticmethod(lambda _t: SA3))
    target: Any = object()
    loadout.apply_target_overrides(target)
    assert loadout.pylon_settings[1][HEAD] == 9
    assert loadout.pylon_settings[2][HEAD] == 4


@pytest.mark.parametrize("clsid", ["{AGM_78A}", "{AGM_78B}"])
def test_standard_arms_have_one_head_and_no_overrides(clsid: str) -> None:
    weapon = Weapon.with_clsid(clsid)
    assert weapon is not None
    assert weapon.get_target_overrides(SA3) == {}
