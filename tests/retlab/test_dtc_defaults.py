"""The DTC tab's starting ticks per task, and the saved per-airframe default (§74)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from game.ato.dtcoptions import ROUTE_RING_RADIUS_NM, DtcOptions
from game.ato.flighttype import FlightType
from game.retlab import dtc_defaults

VIPER = "F-16C_50"


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    path = tmp_path / "dtc_defaults.json"
    monkeypatch.setattr(dtc_defaults, "dtc_defaults_path", lambda: path)
    dtc_defaults.invalidate_cache()
    yield path
    dtc_defaults.invalidate_cache()


def _flight(task: FlightType, is_blue: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        coalition=SimpleNamespace(player=SimpleNamespace(is_blue=is_blue)),
        unit_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id=VIPER)),
        flight_type=task,
        dtc_options=DtcOptions.for_task(task),
    )


def test_front_line_starts_ticked_on_cas_alone() -> None:
    assert DtcOptions.for_task(FlightType.CAS).flot_and_zones
    for task in (FlightType.BARCAP, FlightType.STRIKE, FlightType.SEAD):
        assert not DtcOptions.for_task(task).flot_and_zones


def test_rings_by_task() -> None:
    sead = DtcOptions.for_task(FlightType.SEAD)
    assert sead.threat_ring_radius_nm is None and not sead.long_range_rings_only
    cap = DtcOptions.for_task(FlightType.BARCAP)
    assert cap.threat_ring_radius_nm is None and cap.long_range_rings_only
    for task in (FlightType.STRIKE, FlightType.CAS, FlightType.ESCORT):
        options = DtcOptions.for_task(task)
        assert options.threat_ring_radius_nm == ROUTE_RING_RADIUS_NM
        assert not options.long_range_rings_only
    assert DtcOptions.for_task(FlightType.SEAD_ESCORT).threat_ring_radius_nm is None


def test_saved_default_wins_over_task_ticks(store: Path) -> None:
    mine = DtcOptions.for_task(FlightType.STRIKE)
    mine.threat_ring_radius_nm = 25
    mine.borders = False
    mine.skipped_waypoints = ["NAV"]
    mine.enabled = False
    dtc_defaults.save_default_for(VIPER, FlightType.STRIKE, mine)
    dtc_defaults.invalidate_cache()

    flight = _flight(FlightType.STRIKE)
    dtc_defaults.apply_dtc_defaults(flight)  # type: ignore[arg-type]
    assert flight.dtc_options.threat_ring_radius_nm == 25
    assert not flight.dtc_options.borders
    assert flight.dtc_options.skipped_waypoints == ["NAV"]
    # The on/off override is never saved.
    assert flight.dtc_options.enabled is None


def test_default_is_per_task_and_blue_only(store: Path) -> None:
    mine = DtcOptions.for_task(FlightType.STRIKE)
    mine.borders = False
    dtc_defaults.save_default_for(VIPER, FlightType.STRIKE, mine)

    other_task = _flight(FlightType.CAS)
    dtc_defaults.apply_dtc_defaults(other_task)  # type: ignore[arg-type]
    assert other_task.dtc_options.borders

    red = _flight(FlightType.STRIKE, is_blue=False)
    dtc_defaults.apply_dtc_defaults(red)  # type: ignore[arg-type]
    assert red.dtc_options.borders


def test_clear_and_bad_values(store: Path) -> None:
    mine = DtcOptions.for_task(FlightType.STRIKE)
    dtc_defaults.save_default_for(VIPER, FlightType.STRIKE, mine)
    assert dtc_defaults.has_default_for(VIPER, FlightType.STRIKE)
    dtc_defaults.clear_default_for(VIPER, FlightType.STRIKE)
    assert not dtc_defaults.has_default_for(VIPER, FlightType.STRIKE)

    options = DtcOptions()
    options.apply_saved({"borders": "no", "threat_ring_radius_nm": True, "bogus": 1})
    assert options.borders and options.threat_ring_radius_nm is None


def test_broken_store_is_a_no_op(store: Path) -> None:
    store.write_text("{not json", encoding="utf-8")
    flight = _flight(FlightType.STRIKE)
    dtc_defaults.apply_dtc_defaults(flight)  # type: ignore[arg-type]
    assert flight.dtc_options.threat_ring_radius_nm == ROUTE_RING_RADIUS_NM
