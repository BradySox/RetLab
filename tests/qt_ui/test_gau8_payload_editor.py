"""The GAU-8 selector follows the current payload without changing it on refresh."""

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from dcs import lua
from dcs.planes import A_10C_2

from game import persistency
from game.ato.flightmember import FlightMember
from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.data.gunammunition import GAU8_AMMUNITION
from game.data.weapons import Pylon

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app() -> Any:
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _flight(dcs_unit_type: Any) -> Any:
    return SimpleNamespace(
        unit_type=SimpleNamespace(display_name="Test", dcs_unit_type=dcs_unit_type),
        flight_type=FlightType.CAS,
    )


@pytest.fixture
def editor(app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    from qt_ui.windows.mission.flight.payload.QLoadoutEditor import QLoadoutEditor

    # The §73 default-loadout row reads the payload directory at construction.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16888)
    monkeypatch.setattr(
        Pylon, "iter_pylons", classmethod(lambda cls, aircraft: iter(()))
    )
    member = FlightMember(None, Loadout("Test", {}, None))
    game: Any = SimpleNamespace()
    return QLoadoutEditor(_flight(A_10C_2), member, game)


def test_selector_requires_custom_loadout_and_does_not_mutate_on_refresh(
    editor: Any,
) -> None:
    combo = editor.ammunition_selector
    assert [combo.itemText(i) for i in range(combo.count())] == list(
        GAU8_AMMUNITION.values()
    )
    assert combo.currentData() == 1
    assert not combo.isEnabled()
    assert editor.flight_member.loadout.ammo_type is None
    editor.flight_member.loadout = editor.flight_member.loadout.derive_custom("Custom")
    editor.setChecked(True)
    assert combo.isEnabled()
    combo.setCurrentIndex(combo.findData(2))
    assert editor.flight_member.loadout.ammo_type == 2
    second = FlightMember(None, Loadout("Practice", {}, None, ammo_type=3))
    first = editor.flight_member
    editor.set_flight_member(second)
    assert combo.currentData() == 3
    assert not combo.isEnabled()
    assert first.loadout.ammo_type == 2
    assert second.loadout.ammo_type == 3
    second.loadout = Loadout("Combat", {}, None)
    editor.reset_pylons()
    assert combo.currentData() == 1
    assert second.loadout.ammo_type is None


def test_selector_is_absent_for_other_aircraft(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from qt_ui.windows.mission.flight.payload.QLoadoutEditor import QLoadoutEditor

    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16888)
    monkeypatch.setattr(
        Pylon, "iter_pylons", classmethod(lambda cls, aircraft: iter(()))
    )
    monkeypatch.setattr(
        "game.retlab.loadout_defaults.override_name_for", lambda task, aircraft: "CAS"
    )
    flight = _flight(SimpleNamespace(id="FA-18C_hornet"))
    game: Any = SimpleNamespace()
    editor = QLoadoutEditor(flight, FlightMember(None, Loadout.empty_loadout()), game)
    assert editor.ammunition_selector is None


@pytest.mark.parametrize("ammo", [1, 2, 3, None])
def test_save_payload_round_trip_preserves_ammunition(
    editor: Any, monkeypatch: pytest.MonkeyPatch, ammo: int | None
) -> None:
    from game.retlab import loadout_defaults

    monkeypatch.setattr(A_10C_2, "payloads", {})
    monkeypatch.setattr(
        A_10C_2, "add_to_payload_cache", classmethod(lambda cls, path: None)
    )
    monkeypatch.setattr(A_10C_2, "load_payloads", classmethod(lambda cls: cls.payloads))
    editor.flight_member.loadout.ammo_type = ammo
    assert editor._write_payload("Test ammo")
    path = loadout_defaults.user_payload_file(A_10C_2.id)
    entry = lua.loads(path.read_text(encoding="utf-8"))["unitPayloads"]["payloads"][1]
    assert entry.get("ammo_type") == ammo
    assert next(Loadout.iter_for_aircraft(editor.flight.unit_type)).ammo_type == ammo
    # Updating the same named payload must replace the previous ammunition too.
    editor.flight_member.loadout.ammo_type = 3
    assert editor._write_payload("Test ammo")
    entry = lua.loads(path.read_text(encoding="utf-8"))["unitPayloads"]["payloads"][1]
    assert entry["ammo_type"] == 3
