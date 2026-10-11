"""An empty DATALINK box in the payload editor reads "Auto".

The mission generator fills a blank STN and voice callsign; the bare boxes read as
"nothing is set".
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from typing import Any, Iterator

import pytest
from dcs.planes import FA_18C_hornet


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _box(identifier: str, properties: dict[str, Any]) -> Any:
    from qt_ui.windows.mission.flight.payload.propertyeditbox import PropertyEditBox

    flight = SimpleNamespace(unit_type=SimpleNamespace(dcs_unit_type=FA_18C_hornet))
    member = SimpleNamespace(properties=properties)
    prop = FA_18C_hornet.properties[identifier]
    return PropertyEditBox(member, prop, flight)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "identifier", ["STN_L16", "VoiceCallsignLabel", "VoiceCallsignNumber"]
)
def test_empty_datalink_box_reads_auto(qapp: Any, identifier: str) -> None:
    box = _box(identifier, {})
    assert box.text() == ""
    assert box.placeholderText() == "Auto"


def test_typed_value_shows_instead_of_the_placeholder(qapp: Any) -> None:
    assert _box("STN_L16", {"STN_L16": "00123"}).text() == "00123"
