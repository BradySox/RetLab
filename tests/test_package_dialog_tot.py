"""The package dialog shows the TOT it is given without saving it back.

The spinner's timeChanged is the player's edit. Redrawing through it re-saved the
TOT, which re-ran ASAP, which redrew: RecursionError, 2026-09-27.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime
from types import MethodType, SimpleNamespace
from typing import Any, Iterator, cast

import pytest


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def test_redrawing_the_tot_does_not_save_it(qapp: Any) -> None:
    from PySide6.QtCore import QTime
    from PySide6.QtWidgets import QTimeEdit

    from qt_ui.windows.mission.QPackageDialog import QPackageDialog

    spinner = QTimeEdit(QTime(12, 0))
    saves: list[QTime] = []
    spinner.timeChanged.connect(saves.append)
    package = SimpleNamespace(time_over_target=datetime(2026, 9, 27, 13, 30, 15))
    dialog = SimpleNamespace(
        tot_spinner=spinner, package_model=SimpleNamespace(package=package)
    )
    dialog.tot_qtime = MethodType(QPackageDialog.tot_qtime, dialog)

    QPackageDialog.update_tot(cast(Any, dialog))

    assert spinner.time() == QTime(13, 30, 15)
    assert saves == []


def test_the_players_edit_still_saves(qapp: Any) -> None:
    from PySide6.QtCore import QTime
    from PySide6.QtWidgets import QTimeEdit

    from qt_ui.windows.mission.QPackageDialog import QPackageDialog

    spinner = QTimeEdit(QTime(12, 0))
    saves: list[QTime] = []
    spinner.timeChanged.connect(saves.append)
    package = SimpleNamespace(time_over_target=datetime(2026, 9, 27, 13, 30))
    dialog = SimpleNamespace(
        tot_spinner=spinner, package_model=SimpleNamespace(package=package)
    )
    dialog.tot_qtime = MethodType(QPackageDialog.tot_qtime, dialog)
    QPackageDialog.update_tot(cast(Any, dialog))

    spinner.setTime(QTime(14, 0))

    assert saves == [QTime(14, 0)]
