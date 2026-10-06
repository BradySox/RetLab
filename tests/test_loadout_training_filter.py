"""The Loadout editor's training filter hides choices, never the fitted payload.

Ported from juanjux/dcs-escalation #504/#505, minus white phosphorus: the §38
FAC(A) marks with WP rockets, so they stay listed.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import re
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator
from unittest.mock import Mock

import pytest
from dcs.planes import A_10C_2
from dcs.weapons_data import weapon_ids

from game.ato.flightmember import FlightMember
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon, Weapon, WeaponGroup, WeaponType


@pytest.fixture(scope="module")
def app() -> Any:
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def qt_errors(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # A Qt slot that raises only reaches sys.excepthook; fail the test on it.
    errors: list[Any] = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: errors.append(args))
    yield
    assert not errors


def store(name: str, clsid: str = "test", year: int | None = None) -> Weapon:
    group = WeaponGroup("Test", WeaponType.UNKNOWN, year, None)
    weapon = Weapon(clsid, group)
    object.__setattr__(
        weapon, "pydcs_data", {"name": name, "clsid": clsid, "weight": 100}
    )
    return weapon


@pytest.mark.parametrize(
    "name",
    [
        "Smoke Generator - red",
        "Smokewinder - blue",
        "OV10_SMOKE",
        "LAU-105 - 2 x Captive AIM-9M for ACM",
        "LAU-117 - CATM-65K - Captive Trg Round for Mav K (CCD)",
        "Python-5 Training",
        "R-8R Inert",
        "CBU_DUMMY pod",
        "LAU-68 M274 Practice Smk",
        "BDU-50HD * 6",
        "BRU-41A - 4 x BDU-33",
        "AN/ASQ-T50 TCTS Pod - ACMI Pod",
        "SUU-25 - 8 x Illumination Flare, LUU-2B",
        "SUU-25 * 8 LUU-2",
        "SAB-100MN",
        "LGTR",
        "LAU-117 - TGM-65D - Trg Round for Mav D (IIR)",
        "TGM-65G",
        "MXU-648 Travel Pod",
        "B-8M1 - 20 x UnGd Rkts, 80 mm S-8OM IL",
        "B-8V20A - 20 x UnGd Rkts, 80 mm S-8TsM SM Orange",
        "MATRA F1 - 36 x UnGd Rkts, 68 mm SNEB Type 250 F1B TP-SM",
        "Telson 8 - 8 x UnGd Rkts, 68 mm SNEB Type 252 H1 TP",
        "LAU-131 - 7 x UnGd Rkts, 70 mm Hydra 70 M257 IL",
        "LAU-131 - 7 x UnGd Rkts, 70 mm Hydra 70 Mk 61 TP",
        "BRU-42: 3 x LAU-68 - 7 x UnGd Rkts, 70 mm Hydra 70 WTU-1/B TP",
        "LAU-68 - 7 x UnGd Rkts, 70 mm Hydra 70 Mk 1 HE",
    ],
)
def test_training_and_non_combat_stores_are_hidden(name: str) -> None:
    assert store(name).is_training_or_non_combat


@pytest.mark.parametrize(
    "name",
    [
        "AIM-9M Sidewinder",
        "CBU-105 WCMD",
        "GBU-54 Laser & GPS Guided Bomb",
        "Inertial guided missile",
        "Fuel tank FT600",
        "AN/AAQ-28 LITENING - Targeting Pod",
        "ALQ-184 - ECM Pod",
        "ADM-141 TALD",
        "ALE-40 Dispensers (30 Flares)",
        "KB Flare/Chaff dispenser pod",
        "Mk-84 AIR TP * 2",
        "SM-2 Standard Missile",
        "APU-68 - S-24B - 240mm UnGd Rkt, 235kg, HE/Frag, (Low Smk)",
        "LAU-131 - 7 x UnGd Rkts, 70 mm Hydra 70 M151 HE",
        "LAU-68 - 7 x UnGd Rkts, 70 mm Hydra 70 Mk 5 HEAT",
        "Clean",
        "Unknown mod store",
    ],
)
def test_combat_and_support_stores_stay_visible(name: str) -> None:
    assert not store(name).is_training_or_non_combat


@pytest.mark.parametrize(
    "name",
    [
        "LAU-131 M156 WP",
        "LAU-131 - 7 x UnGd Rkts, 70 mm Hydra 70 M156 SM",
        "BRU-42: 3 x LAU-68 - 7 x UnGd Rkts, 70 mm Hydra 70 M156 SM",
        "LAU-68 - 7 x UnGd Rkts, 70 mm Mk 4 FFAR M156 SM",
        '2x LAU-3 pod - 19 x 2.75" FFAR, UnGd Rkts M156, Wht Phos (TER)',
    ],
)
def test_white_phosphorus_marking_rockets_stay_visible(name: str) -> None:
    assert not store(name).is_training_or_non_combat


def test_no_white_phosphorus_store_in_pydcs_is_hidden() -> None:
    group = WeaponGroup("Test", WeaponType.UNKNOWN, None, None)
    wp = re.compile(r"\b(WP|M156)\b|\bWht\s+Phos", re.IGNORECASE)
    pydcs: dict[str, Any] = weapon_ids
    names = {clsid: data["name"] for clsid, data in pydcs.items()}
    wp_clsids = [c for c, name in names.items() if wp.search(name)]
    assert len(wp_clsids) > 20
    hidden = [names[c] for c in wp_clsids if Weapon(c, group).is_training_or_non_combat]
    assert hidden == []


def test_clsid_identifies_short_mod_names() -> None:
    assert store("Sidewinder", "{MOD_LAU127_CATM-9M}").is_training_or_non_combat


@pytest.fixture
def setup_editor(app: Any) -> Any:
    from qt_ui.windows.mission.flight.payload.QPylonEditor import QPylonEditor

    live = store("AIM-9M", "live")
    captive = store("Captive AIM-9M", "captive")
    wp = store("LAU-131 - 7 x UnGd Rkts, 70 mm Hydra 70 M156 SM", "wp")
    future = store("Future training round", "future", 2099)
    pylon = Pylon(1, {live, captive, wp, future})
    member = FlightMember(None, Loadout("Custom", {1: live}, None, True))
    game: Any = SimpleNamespace(
        settings=SimpleNamespace(
            restrict_weapons_by_date=False, apply_target_overrides_to_loadouts=False
        ),
        date=date(2000, 1, 1),
    )
    flight: Any = SimpleNamespace(
        squadron=SimpleNamespace(coalition=SimpleNamespace(faction=SimpleNamespace())),
        unit_type=None,
    )
    return SimpleNamespace(
        editor=QPylonEditor(game, flight, member, pylon),
        live=live,
        captive=captive,
        wp=wp,
        future=future,
        member=member,
        flight=flight,
        game=game,
        pylon=pylon,
    )


def test_filter_defaults_off_and_never_changes_payload(setup_editor: Any) -> None:
    data = setup_editor
    editor = data.editor
    combo = editor.weapon_combo
    changed = Mock()
    editor.pylon_changed.connect(changed)
    data.member.loadout.pylon_settings[1] = {"laser_code": 1688}
    assert combo.findData(data.captive) == -1
    assert combo.findData(data.wp) >= 0
    assert combo.currentData() == data.live
    for show in (True, False, True, False):
        editor.set_show_training(show)
        assert (combo.findData(data.captive) >= 0) == show
        assert combo.findData(data.wp) >= 0
        assert combo.currentData() == data.live
        assert data.member.loadout.pylons == {1: data.live}
        assert data.member.loadout.pylon_settings == {1: {"laser_code": 1688}}
    changed.assert_not_called()


def test_fitted_training_store_stays_until_replaced(setup_editor: Any) -> None:
    data = setup_editor
    editor = data.editor
    combo = editor.weapon_combo
    editor.set_show_training(True)
    combo.setCurrentIndex(combo.findData(data.captive))
    data.member.loadout.pylon_settings[1] = {"test": 42}
    editor.set_show_training(False)
    assert combo.currentData() == data.captive
    assert data.member.loadout.pylons[1] == data.captive
    assert data.member.loadout.pylon_settings[1] == {"test": 42}
    combo.setCurrentIndex(combo.findData(data.live))
    assert combo.findData(data.captive) == -1
    assert 1 not in data.member.loadout.pylon_settings
    combo.setCurrentIndex(0)
    assert data.member.loadout.pylons[1] is None


def test_preset_with_a_hidden_store_still_shows_it(setup_editor: Any) -> None:
    data = setup_editor
    training = Loadout("Training", {1: data.captive}, None)
    data.member.loadout = training
    data.editor.set_from(training)
    assert data.editor.weapon_combo.currentData() == data.captive
    second = FlightMember(None, Loadout("Combat", {1: data.live}, None))
    data.editor.set_flight_member(second)
    assert data.editor.weapon_combo.currentData() == data.live
    assert data.editor.weapon_combo.findData(data.captive) == -1
    assert training.pylons == {1: data.captive}


def test_clean_pylon_survives_filter_changes(setup_editor: Any) -> None:
    clean = Weapon.with_clsid("<CLEAN>")
    assert clean is not None
    data = setup_editor
    data.member.loadout = Loadout("Clean", {1: clean}, None)
    data.editor.set_from(data.member.loadout)
    for show in (True, False, True):
        data.editor.set_show_training(show)
        assert data.editor.weapon_combo.currentData() == clean
        assert data.member.loadout.pylons[1] == clean


def test_show_training_still_respects_date_restrictions(setup_editor: Any) -> None:
    from qt_ui.windows.mission.flight.payload.QPylonEditor import QPylonEditor

    data = setup_editor
    data.game.settings.restrict_weapons_by_date = True
    editor = QPylonEditor(data.game, data.flight, data.member, data.pylon)
    editor.set_show_training(True)
    assert editor.weapon_combo.findData(data.captive) >= 0
    assert editor.weapon_combo.findData(data.future) == -1


def test_checkbox_updates_every_pylon(
    setup_editor: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from game import persistency
    from game.ato.flighttype import FlightType
    from qt_ui.windows.mission.flight.payload.QLoadoutEditor import QLoadoutEditor

    # The §73 default-loadout row reads the payload directory at construction.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16888)
    data = setup_editor
    monkeypatch.setattr(
        Pylon,
        "iter_pylons",
        classmethod(
            lambda cls, aircraft: iter([data.pylon, Pylon(2, data.pylon.allowed)])
        ),
    )
    data.flight.unit_type = SimpleNamespace(
        display_name="A-10C II", dcs_unit_type=A_10C_2
    )
    data.flight.flight_type = FlightType.CAS
    editor = QLoadoutEditor(data.flight, data.member, data.game)
    assert not editor.show_training_check.isChecked()
    for show in (True, False):
        editor.show_training_check.setChecked(show)
        for pylon in editor.iter_pylon_editors():
            assert (pylon.weapon_combo.findData(data.captive) >= 0) == show
    assert data.member.loadout.pylons == {1: data.live}
