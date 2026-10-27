"""Tests for coordinate formatting helpers."""

from __future__ import annotations

import pytest

from dcs.terrain.caucasus.caucasus import Caucasus
from dcs.terrain.germanycoldwar import GermanyColdWar
from dcs.terrain.nevada import Nevada
from dcs.mapping import LatLng, Point

from game.missiongenerator.kneeboard_recon.coords import (
    bullseye_bearing_range_nm,
    point_to_dms,
    point_to_mgrs,
)
from game.utils import Heading


@pytest.fixture(scope="module")
def caucasus() -> Caucasus:
    return Caucasus()


def test_point_to_mgrs_is_38t_for_tbilisi(caucasus: Caucasus) -> None:
    # Tbilisi-Lochini is roughly (41.66 N, 44.95 E) which is MGRS zone 38T MM.
    p = Point.from_latlng(LatLng(41.6692, 44.9547), caucasus)
    result = point_to_mgrs(p)
    assert result.startswith("38T MM "), f"expected 38T MM prefix, got {result!r}"
    parts = result.split()
    assert len(parts) == 3
    assert len(parts[2]) == 10  # easting (5) + northing (5)


def test_point_to_mgrs_uses_five_digit_precision(caucasus: Caucasus) -> None:
    p = Point.from_latlng(LatLng(41.6692, 44.9547), caucasus)
    result = point_to_mgrs(p)
    parts = result.split()
    assert parts[2].isdigit()
    assert len(parts[2]) == 10


def test_point_to_dms_formats_with_decimal_seconds(caucasus: Caucasus) -> None:
    # Format is degrees-minutes-seconds with compass suffix, e.g. 41°40'9.12"N
    p = Point.from_latlng(LatLng(41.6692, 44.9547), caucasus)
    result = point_to_dms(p)
    assert "41°" in result
    assert "N" in result
    assert "44°" in result
    assert "E" in result
    # Decimal seconds are present (format: DD°MM'SS.ss"<dir>)
    assert '"' in result


def test_point_to_dms_west_of_greenwich() -> None:
    """pydcs printed Nevada as -115°42'...W: a stray minus and the wrong minutes."""
    p = Point.from_latlng(LatLng(36.2, -115.3), Nevada())
    result = point_to_dms(p)
    assert result.startswith("36°12'")
    assert " 115°18'" in result
    assert result.endswith('"W')
    assert "-" not in result


def test_bullseye_bearing_range_nm_due_east(caucasus: Caucasus) -> None:
    bullseye = Point.from_latlng(LatLng(43.0, 41.0), caucasus)
    target = Point.from_latlng(LatLng(43.0, 41.0228), caucasus)
    bearing, range_nm = bullseye_bearing_range_nm(bullseye, target)
    assert bearing == Heading.from_degrees(90)
    assert range_nm == pytest.approx(1.0, abs=0.01)


def test_bullseye_bearing_range_nm_due_south(caucasus: Caucasus) -> None:
    bullseye = Point.from_latlng(LatLng(43.0, 41.0), caucasus)
    target = Point.from_latlng(LatLng(43.0 - 5 / 60, 41.0), caucasus)
    bearing, range_nm = bullseye_bearing_range_nm(bullseye, target)
    assert bearing == Heading.from_degrees(180)
    assert range_nm == pytest.approx(5.0, abs=0.05)


def test_bullseye_bearing_is_true_not_grid() -> None:
    # Test 65: on the Germany map the grid runs about 10 degrees off true.
    germany = GermanyColdWar()
    bullseye = Point.from_latlng(LatLng(50.5, 10.0), germany)
    target = Point.from_latlng(LatLng(51.0, 10.0), germany)
    grid = bullseye.heading_between_point(target)
    assert min(grid % 360, 360 - grid % 360) > 5
    bearing, _ = bullseye_bearing_range_nm(bullseye, target)
    assert bearing == Heading.from_degrees(0)
