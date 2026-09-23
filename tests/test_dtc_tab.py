"""The Edit Flight DTC tab writes flight.dtc_options live (§74).

Drives the real widget offscreen with faked Flight/Game: the master combo's
tri-state maps to DtcOptions.enabled, the contents group greys out whenever the
resolved state is off (including the follow-campaign case), and each section
checkbox writes its field.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from typing import Any, Iterator

import pytest
from PySide6.QtWidgets import QApplication

from game.ato.dtcoptions import DtcOptions


@pytest.fixture(scope="module", autouse=True)
def _qt_app() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    yield app


def _tab(*, campaign_on: bool = True, options: DtcOptions | None = None) -> Any:
    from qt_ui.windows.mission.flight.QFlightDtcTab import QFlightDtcTab

    flight = SimpleNamespace(dtc_options=options or DtcOptions())
    game = SimpleNamespace(settings=SimpleNamespace(dtc_data_cartridges=campaign_on))
    return QFlightDtcTab(flight, game), flight  # type: ignore[arg-type]


def _enabled(flight: Any) -> object:
    # Read through a helper so mypy does not narrow the member expression
    # across the sequential asserts (it flags the later ones unreachable).
    return flight.dtc_options.enabled


def test_master_combo_maps_the_tristate() -> None:
    tab, flight = _tab()
    assert tab.mode_selector.currentIndex() == 0
    assert tab.contents_group.isEnabled()

    tab.mode_selector.setCurrentIndex(2)  # Never load
    assert _enabled(flight) is False
    assert not tab.contents_group.isEnabled()

    tab.mode_selector.setCurrentIndex(1)  # Always load
    assert _enabled(flight) is True
    assert tab.contents_group.isEnabled()

    tab.mode_selector.setCurrentIndex(0)  # Follow campaign
    assert _enabled(flight) is None


def test_follow_campaign_greys_when_the_setting_is_off() -> None:
    tab, flight = _tab(campaign_on=False)
    assert "off" in tab.mode_selector.itemText(0)
    assert not tab.contents_group.isEnabled()
    tab.mode_selector.setCurrentIndex(1)  # per-flight override wins
    assert tab.contents_group.isEnabled()


def test_section_checkboxes_write_the_options() -> None:
    tab, flight = _tab()
    by_attr = {attr: box for box, attr in tab.section_boxes}
    assert set(by_attr) == {
        "comms",
        "route",
        "nav_aids",
        "flot_and_zones",
        "friendly_orbits",
        "threat_rings",
        "destinations",
        "jdam_targets",
        "roe_table",
        "countermeasures",
        "saved_points",
        "drawings",
    }
    # Every section is on by default except countermeasures, which waits on the
    # flown CMDS check (B28).
    defaults = DtcOptions()
    assert {attr: box.isChecked() for attr, box in by_attr.items()} == {
        attr: getattr(defaults, attr) for attr in by_attr
    }
    assert by_attr["countermeasures"].isChecked() is False

    by_attr["threat_rings"].setChecked(False)
    assert flight.dtc_options.threat_rings is False
    by_attr["threat_rings"].setChecked(True)
    assert flight.dtc_options.threat_rings is True


def test_existing_choices_are_reflected() -> None:
    options = DtcOptions(enabled=False, comms=False)
    tab, _ = _tab(options=options)
    assert tab.mode_selector.currentIndex() == 2
    by_attr = {attr: box for box, attr in tab.section_boxes}
    assert not by_attr["comms"].isChecked()
    assert by_attr["route"].isChecked()


def _typed_tab(dcs_id: str, waypoint_types: list[str]) -> Any:
    from game.ato.flightwaypointtype import FlightWaypointType
    from qt_ui.windows.mission.flight.QFlightDtcTab import QFlightDtcTab

    flight = SimpleNamespace(
        dtc_options=DtcOptions(),
        unit_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id=dcs_id)),
        flight_plan=SimpleNamespace(
            waypoints=[
                SimpleNamespace(waypoint_type=FlightWaypointType[name])
                for name in waypoint_types
            ]
        ),
    )
    game = SimpleNamespace(settings=SimpleNamespace(dtc_data_cartridges=True))
    return QFlightDtcTab(flight, game), flight  # type: ignore[arg-type]


def test_a_hornet_is_offered_only_what_its_cartridge_carries() -> None:
    tab, _ = _typed_tab("FA-18C_hornet", ["TAKEOFF", "NAV", "LANDING_POINT"])
    offered = {attr for _box, attr in tab.section_boxes}
    assert "nav_aids" in offered and "saved_points" in offered
    assert not offered & {"roe_table", "destinations", "jdam_targets", "comms"}


def test_unticking_a_waypoint_kind_skips_it() -> None:
    from PySide6.QtCore import Qt

    tab, flight = _typed_tab("F-16C_50", ["TAKEOFF", "JOIN", "NAV", "NAV", "SPLIT"])
    listing = tab.waypoint_list
    names = [
        listing.item(i).data(Qt.ItemDataRole.UserRole) for i in range(listing.count())
    ]
    assert names == ["JOIN", "NAV", "SPLIT"]  # the takeoff row is never offered
    listing.item(0).setCheckState(Qt.CheckState.Unchecked)
    assert flight.dtc_options.skipped_waypoints == ["JOIN"]
    listing.item(0).setCheckState(Qt.CheckState.Checked)
    assert flight.dtc_options.skipped_waypoints == []


def test_the_sam_filter_writes_a_radius_only_when_ticked() -> None:
    tab, flight = _typed_tab("F-16C_50", ["TAKEOFF"])
    assert flight.dtc_options.threat_ring_radius_nm is None
    tab.threat_near_route.setChecked(True)
    tab.threat_radius.setValue(15)
    assert flight.dtc_options.threat_ring_radius_nm == 15
    tab.threat_near_route.setChecked(False)
    assert flight.dtc_options.threat_ring_radius_nm is None


def test_load_timing_writes_auto_load() -> None:
    tab, flight = _typed_tab("F-16C_50", ["TAKEOFF"])
    tab.load_selector.setCurrentIndex(1)
    assert flight.dtc_options.auto_load is False


def test_waypoint_types_read_as_the_plan_names_them() -> None:
    tab, _ = _typed_tab("F-16C_50", ["TAKEOFF", "INGRESS_SEAD", "LOITER"])
    listing = tab.waypoint_list
    labels = [listing.item(i).text() for i in range(listing.count())]
    assert labels == ["Ingress (SEAD)  (1)", "Hold  (1)"]


def test_the_skip_note_is_true_for_the_airframe() -> None:
    # Only the jets whose cartridge route replaces the editor's renumber the
    # kneeboard; the Tomcat's route is plan 2 and the kneeboard keeps every row.
    viper, _ = _typed_tab("F-16C_50", ["TAKEOFF", "NAV"])
    tomcat, _ = _typed_tab("F-14BU", ["TAKEOFF", "NAV"])
    assert "prints '-'" in viper._waypoint_picker_note()
    assert "prints '-'" not in tomcat._waypoint_picker_note()
