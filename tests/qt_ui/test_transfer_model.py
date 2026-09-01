"""Qt transfer authorization and catalog contracts (ownership slice).

These tests verify live owner-based ground purchase authorization, RED
ground-forces tab gating, captured-faction catalogs, and the transfer
submit-eligibility guard.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from game.dcs.groundunittype import GroundUnitType
from game.purchaseadapter import GroundUnitPurchaseAdapter, TransactionError
from game.theater.player import Player
from qt_ui.windows.basemenu.NewUnitTransferDialog import NewUnitTransferDialog

# ---------------------------------------------------------------------------
# Qt application fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def app() -> QApplication:
    return cast(QApplication, QApplication.instance() or QApplication([]))


@pytest.fixture(autouse=True)
def _seed_icons(app: QApplication) -> Any:
    """Populate uiconstants ICONS so widgets can construct headless.

    Some Qt widget ``initUi`` methods read several ``CONST.ICONS`` keys that
    are only populated by ``load_icons()`` (which needs the real resource
    files). Seed blank pixmaps for any missing keys so widgets build under
    offscreen Qt. Depends on ``app`` so a QApplication exists first.
    """
    import qt_ui.uiconstants as CONST
    from PySide6.QtGui import QPixmap

    for key in [
        "Generator",
        "Cheat",
        "Plugins",
        "PluginsOptions",
        "Settings",
    ]:
        if key not in CONST.ICONS:
            CONST.ICONS[key] = QPixmap()
    yield


# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------


class FakeTransferModel(QObject):
    inventory_changed = Signal()


class FakePurchaseAdapter:
    def __init__(self, current: int) -> None:
        self.current = current
        self.coalition = SimpleNamespace(budget=100)

    def buy(self, _item: str, quantity: int) -> None:
        self.current += quantity

    def sell(self, _item: str, quantity: int) -> None:
        self.current -= quantity

    def current_quantity_of(self, _item: str) -> int:
        return self.current

    def pending_delivery_quantity(self, _item: str) -> int:
        return 0

    def expected_quantity_next_turn(self, item: str) -> int:
        return self.current_quantity_of(item)

    def name_of(self, item: str, multiline: bool = False) -> str:
        return item if not multiline else f"{item}<br />"

    def price_of(self, _item: str) -> int:
        return 1

    def can_buy(self, _item: str) -> bool:
        return True

    def can_sell_or_cancel(self, _item: str) -> bool:
        return self.current > 0

    def unit_type_of(self, _item: str) -> Any:
        return object()


def _game_model(game: Any, transfer_model: Any = None) -> Any:
    if transfer_model is None:
        transfer_model = MagicMock()
    return SimpleNamespace(game=game, transfer_model=transfer_model)


def _ground_purchase_fixture(
    transfer_model: Any,
) -> tuple[Any, GroundUnitType, Any]:
    unit_type = cast(GroundUnitType, MagicMock(price=5, display_name="Tank"))
    orders = SimpleNamespace(_pending=0)
    orders.pending_orders = lambda _unit_type: orders._pending
    orders.order = lambda _units: setattr(orders, "_pending", orders._pending + 1)
    orders.sell = lambda _units: setattr(orders, "_pending", orders._pending - 1)
    cp = SimpleNamespace(
        captured=Player.BLUE,
        ground_unit_orders=orders,
        base=SimpleNamespace(total_units_of_type=lambda _unit_type: 0),
        has_ground_unit_source=lambda _game: True,
    )
    coalition: Any = SimpleNamespace(
        budget=100,
        adjust_budget=lambda amount: setattr(
            coalition, "budget", coalition.budget + amount
        ),
    )
    game = SimpleNamespace(settings=SimpleNamespace(enable_enemy_buy_sell=False))
    adapter = GroundUnitPurchaseAdapter(
        cast(Any, cp),
        cast(Any, coalition),
        cast(Any, game),
    )
    return cp, unit_type, adapter


# ---------------------------------------------------------------------------
# Base menu tabs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("enemy_buy_sell", "expected_tabs"),
    [
        (False, ["Intel", "Departing Convoys"]),
        (True, ["Intel", "Departing Convoys", "Ground Forces HQ"]),
    ],
)
def test_red_base_menu_exposes_authorized_ground_forces_tab(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    enemy_buy_sell: bool,
    expected_tabs: list[str],
) -> None:
    """RED keeps its informational tabs and gates Ground Forces HQ by setting."""
    from qt_ui.windows.basemenu import QBaseMenuTabs as tabs_module

    class StubIntel(QWidget):
        def __init__(self, _cp: Any) -> None:
            super().__init__()

    class StubConvoys(QWidget):
        def __init__(self, _cp: Any, _game_model: Any) -> None:
            super().__init__()

    class StubGroundForces(QWidget):
        def __init__(self, _cp: Any, _game_model: Any) -> None:
            super().__init__()

    monkeypatch.setattr(tabs_module, "QIntelInfo", StubIntel)
    monkeypatch.setattr(tabs_module, "DepartingConvoysMenu", StubConvoys)
    monkeypatch.setattr(tabs_module, "QGroundForcesHQ", StubGroundForces)

    cp = SimpleNamespace(captured=Player.RED)
    game_model = SimpleNamespace(
        game=SimpleNamespace(
            settings=SimpleNamespace(enable_enemy_buy_sell=enemy_buy_sell)
        )
    )

    tabs = tabs_module.QBaseMenuTabs(cast(Any, cp), cast(Any, game_model))

    assert [tabs.tabText(index) for index in range(tabs.count())] == expected_tabs


def test_neutral_base_menu_does_not_expose_ground_forces_tab(
    app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Neutral control points do not expose the ground-forces catalog."""
    from qt_ui.windows.basemenu import QBaseMenuTabs as tabs_module

    class StubAirfield(QWidget):
        def __init__(self, _cp: Any, _game_model: Any) -> None:
            super().__init__()

    class StubGroundForces(QWidget):
        def __init__(self, _cp: Any, _game_model: Any) -> None:
            super().__init__()

    monkeypatch.setattr(tabs_module, "QAirfieldCommand", StubAirfield)
    monkeypatch.setattr(tabs_module, "QGroundForcesHQ", StubGroundForces)

    cp = SimpleNamespace(
        captured=Player.NEUTRAL,
        can_deploy_ground_units=True,
    )
    game_model = SimpleNamespace(game=SimpleNamespace(settings=SimpleNamespace()))

    tabs = tabs_module.QBaseMenuTabs(cast(Any, cp), cast(Any, game_model))

    assert "Ground Forces HQ" not in [
        tabs.tabText(index) for index in range(tabs.count())
    ]


# ---------------------------------------------------------------------------
# Purchase authorization
# ---------------------------------------------------------------------------


def test_ground_purchase_authorization_is_live_and_owner_based() -> None:
    """Ground purchases follow the current owner and RED's live setting."""
    transfer_model = FakeTransferModel()
    cp, unit_type, adapter = _ground_purchase_fixture(transfer_model)
    cp.captured = Player.RED

    assert not adapter.can_buy(unit_type)
    with pytest.raises(TransactionError):
        adapter.buy(unit_type, 1)
    assert cp.ground_unit_orders.pending_orders(unit_type) == 0

    adapter.game.settings.enable_enemy_buy_sell = True
    assert adapter.can_buy(unit_type)
    adapter.buy(unit_type, 1)
    assert cp.ground_unit_orders.pending_orders(unit_type) == 1

    adapter.game.settings.enable_enemy_buy_sell = False
    with pytest.raises(TransactionError):
        adapter.sell(unit_type, 1)
    assert cp.ground_unit_orders.pending_orders(unit_type) == 1


def test_ground_purchase_direct_neutral_calls_are_denied() -> None:
    """Neutral owners cannot buy or cancel ground-unit orders directly."""
    transfer_model = FakeTransferModel()
    cp, unit_type, adapter = _ground_purchase_fixture(transfer_model)
    cp.captured = Player.NEUTRAL
    cp.ground_unit_orders.order({unit_type: 1})

    assert not adapter.can_buy(unit_type)
    assert not adapter.can_sell(unit_type)
    assert not adapter.can_sell_or_cancel(unit_type)
    with pytest.raises(TransactionError):
        adapter.buy(unit_type, 1)
    with pytest.raises(TransactionError):
        adapter.sell(unit_type, 1)
    assert cp.ground_unit_orders.pending_orders(unit_type) == 1


# ---------------------------------------------------------------------------
# Captured-faction catalog
# ---------------------------------------------------------------------------


def test_armor_recruitment_menu_uses_captured_faction_catalog(
    app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A RED menu lists RED units while enemy buy/sell authorization is enabled."""
    from qt_ui.windows.basemenu.ground_forces.QArmorRecruitmentMenu import (
        QArmorRecruitmentMenu,
    )
    from qt_ui.windows.GameUpdateSignal import GameUpdateSignal

    monkeypatch.setattr(
        GameUpdateSignal,
        "get_instance",
        lambda: SimpleNamespace(updateBudget=lambda _game: None),
    )
    blue_unit = cast(GroundUnitType, MagicMock(display_name="Blue tank", price=5))
    red_unit = cast(GroundUnitType, MagicMock(display_name="Red tank", price=5))
    blue_faction = SimpleNamespace(ground_units={blue_unit})
    red_faction = SimpleNamespace(ground_units={red_unit})
    orders = SimpleNamespace(pending_orders=lambda _unit: 0)
    game = SimpleNamespace(
        settings=SimpleNamespace(enable_enemy_buy_sell=True),
        faction_for=lambda player: (
            blue_faction if player is Player.BLUE else red_faction
        ),
        coalition_for=lambda player: SimpleNamespace(
            faction=blue_faction if player is Player.BLUE else red_faction,
            transfers=SimpleNamespace(),
            budget=100,
        ),
    )
    cp = SimpleNamespace(
        captured=Player.RED,
        ground_unit_orders=orders,
        base=SimpleNamespace(total_units_of_type=lambda _unit: 3),
        has_ground_unit_source=lambda _game: True,
    )
    game_model = SimpleNamespace(game=game, transfer_model=FakeTransferModel())

    menu = QArmorRecruitmentMenu(cast(Any, cp), cast(Any, game_model))

    assert set(menu.purchase_groups) == {red_unit}
    assert menu.purchase_groups[red_unit].sell_button.isHidden()


# ---------------------------------------------------------------------------
# Submit eligibility
# ---------------------------------------------------------------------------


def test_transfer_submit_requires_eligible_destination(
    app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Selected units cannot be submitted when no destination is available."""
    submitted: list[Any] = []
    monkeypatch.setattr(
        "qt_ui.windows.basemenu.NewUnitTransferDialog.submit_transfer",
        lambda *args, **kwargs: submitted.append((args, kwargs)),
    )
    monkeypatch.setattr(NewUnitTransferDialog, "close", lambda _self: None)
    dialog = NewUnitTransferDialog.__new__(NewUnitTransferDialog)
    cast(Any, dialog).submit_button = QPushButton()
    cast(Any, dialog).transfer_panel = SimpleNamespace(transfers={"tank": 1})
    cast(Any, dialog).dest_panel = SimpleNamespace(current=None, request_airlift=False)
    cast(Any, dialog).game_model = SimpleNamespace(
        sim_controller=SimpleNamespace(current_time_in_sim=0)
    )
    cast(Any, dialog).origin = object()

    dialog.on_transfer_quantity_changed()
    dialog.on_submit()

    assert dialog.submit_button.isEnabled() is False
    assert submitted == []
