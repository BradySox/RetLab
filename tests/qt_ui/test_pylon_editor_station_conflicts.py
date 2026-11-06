"""Picking an F-4E inboard rack empties the rails it blocks, and the reverse."""

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from dcs.planes import F_4E_45MC

from game import persistency
from game.ato.flightmember import FlightMember
from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.data.weapons import Weapon

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

AIM_9L = "{AIM-9L}"
MK83_TER = "{HB_F4E_MK-83_3x}"
MK82_SWA = "{HB_F4E_MK-82_2x_SWA}"


@pytest.fixture(scope="module")
def app() -> Any:
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def editor(app: Any, tmp_path: Path) -> Any:
    from qt_ui.windows.mission.flight.payload.QLoadoutEditor import QLoadoutEditor

    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16887)
    rails = {n: Weapon.with_clsid(AIM_9L) for n in (2, 4, 10, 12)}
    member = FlightMember(None, Loadout("Custom", rails, None, is_custom=True))
    flight: Any = SimpleNamespace(
        unit_type=SimpleNamespace(display_name="F-4E", dcs_unit_type=F_4E_45MC),
        flight_type=FlightType.STRIKE,
    )
    game: Any = SimpleNamespace(
        settings=SimpleNamespace(
            restrict_weapons_by_date=False, apply_target_overrides_to_loadouts=False
        )
    )
    return QLoadoutEditor(flight, member, game)


def _station(editor: Any, number: int) -> Any:
    return next(e for e in editor.iter_pylon_editors() if e.pylon.number == number)


def _pick(editor: Any, number: int, clsid: str) -> None:
    combo = _station(editor, number).weapon_combo
    weapon = Weapon.with_clsid(clsid)
    index = next(i for i in range(combo.count()) if combo.itemData(i) == weapon)
    combo.setCurrentIndex(index)


def _fit(editor: Any) -> dict[int, str]:
    pylons = editor.flight_member.loadout.pylons
    return {n: w.clsid for n, w in pylons.items() if w is not None}


def test_a_ter_inboard_empties_that_wings_rails(editor: Any) -> None:
    _pick(editor, 3, MK83_TER)
    assert _fit(editor) == {3: MK83_TER, 10: AIM_9L, 12: AIM_9L}
    assert _station(editor, 2).weapon_combo.currentText() == "None"
    assert _station(editor, 4).weapon_combo.currentText() == "None"
    _pick(editor, 4, AIM_9L)
    assert _fit(editor) == {4: AIM_9L, 10: AIM_9L, 12: AIM_9L}
    assert _station(editor, 3).weapon_combo.currentText() == "None"


def test_an_swa_load_keeps_the_rails(editor: Any) -> None:
    _pick(editor, 11, MK82_SWA)
    assert _fit(editor)[10] == AIM_9L
    assert _fit(editor)[12] == AIM_9L
