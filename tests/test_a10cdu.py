"""The A-10's saved points, written into the mission beside its own route.

It has no cartridge, so the saved points go where "Prepare Mission" puts the cockpit:
Avionics/<type>/<unit>/CDU/SETTINGS.lua. The route is left to DCS. Everything pinned
here was measured against DCS's own output, because there is no document.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional, cast

import pytest
from dcs.lua import loads
from dcs.mapping import Point
from dcs.point import MovingPoint, PointProperties, Scale, Steer, VNav
from dcs.terrain import Caucasus

from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.savedpoints import PointKind, SavedPoint
from game.missiongenerator import a10cdu


class _Terrain:
    """Enough of one to turn a position into a latitude and a longitude."""

    name = "Caucasus"


def _latlng(x: float, y: float) -> Any:
    return SimpleNamespace(lat=42.0 + x / 100000.0, lng=42.0 + y / 100000.0)


def _waypoint(name: str, x: float, y: float) -> Any:
    return SimpleNamespace(
        display_name=name,
        position=SimpleNamespace(x=x, y=y),
        alt=SimpleNamespace(meters=0.0),
        alt_type="BARO",
        waypoint_type=FlightWaypointType.TARGET_POINT,
    )


def _point(name: str, x: float = 1000.0, y: float = 2000.0) -> SavedPoint:
    return SavedPoint(kind=PointKind.WAYPOINT, name=name, x=x, y=y)


def _flight(
    aircraft: str = "A-10C_2",
    route: int = 4,
    saved: Optional[list[SavedPoint]] = None,
    crewed: int = 1,
) -> Any:
    return SimpleNamespace(
        aircraft_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id=aircraft)),
        client_units=[SimpleNamespace(id=7)] * crewed,
        units=[SimpleNamespace(id=7)],
        waypoints=[_waypoint(f"LEG{n}", float(n), float(n)) for n in range(route)],
        saved_points=saved if saved is not None else [],
    )


def _settings(flight: Any, monkeypatch: Any) -> str:
    monkeypatch.setattr(
        a10cdu,
        "Point",
        lambda x, y, terrain: SimpleNamespace(latlng=lambda: _latlng(x, y)),
    )
    return a10cdu.settings(flight, _Terrain())


def _database(flight: Any, monkeypatch: Any) -> Any:
    return loads(_settings(flight, monkeypatch))["settings"]


# ------------------------------------------------- where it goes and what is in it


def test_it_goes_where_prepare_mission_puts_the_cockpit() -> None:
    assert a10cdu.inside_mission(_flight()) == "Avionics/A-10C_2/7/CDU/SETTINGS.lua"


def test_the_terrain_system_is_switched_on(monkeypatch: Any) -> None:
    written = _settings(_flight(saved=[_point("SMOKE")]), monkeypatch)

    assert '["dtsas_func"]=1' in written
    assert '["dtsas_cr"]=1' in written


@pytest.mark.parametrize("aircraft", ["A-10C", "A-10C_2"])
def test_the_route_is_left_to_dcs(aircraft: str, monkeypatch: Any) -> None:
    """Writing the route here made the aircraft swap each waypoint's planned altitude
    for the terrain height (flown, escalation #511)."""
    flight = _flight(aircraft=aircraft, route=8, saved=[_point("OIL")])

    settings = _database(flight, monkeypatch)

    assert set(settings["waypoints"]) == {8}
    assert settings["waypoints"][8]["wpt_id"] == "OIL"
    extra = settings["flight_plans"][a10cdu.EXTRA_PLAN]["waypoints"]
    assert extra[1]["wpt_number"] == 8


@pytest.mark.parametrize("kind", list(FlightWaypointType))
def test_no_kind_of_route_point_is_written(
    kind: FlightWaypointType, monkeypatch: Any
) -> None:
    flight = _flight(route=2, saved=[_point("OIL")])
    flight.waypoints[1].waypoint_type = kind

    cdu = _database(flight, monkeypatch)["waypoints"]

    assert set(cdu) == {2}
    assert cdu[2]["wpt_id"] == "OIL"


def test_the_aircraft_keeps_its_own_first_point(monkeypatch: Any) -> None:
    """A second INIT POSIT in slot 1 pushed HOLD and everything after it up by one."""
    flight = _flight(route=3, saved=[_point("OIL")])
    flight.waypoints[0].display_name = "Takeoff"
    flight.waypoints[1].display_name = "Hold"

    written = _settings(flight, monkeypatch)
    cdu = loads(written)["settings"]["waypoints"]

    assert "INIT POSIT" not in written
    assert "TAKEOFF" not in written
    assert "HOLD" not in written
    assert not set(cdu).intersection(range(len(flight.waypoints)))
    assert cdu[3]["wpt_id"] == "OIL"


@pytest.mark.parametrize("height_ft", [0, 1234, -100])
def test_a_saved_point_carries_its_own_elevation_in_metres(
    monkeypatch: Any, height_ft: int
) -> None:
    point = _point("SMOKE")
    point.altitude_ft = height_ft

    cdu = _database(_flight(saved=[point]), monkeypatch)["waypoints"]

    assert cdu[4]["wpt_elev"] == pytest.approx(height_ft * 0.3048)
    assert cdu[4]["wpt_elev_present"] == 1


@pytest.mark.parametrize("aircraft", ["A-10C", "A-10C_2"])
def test_every_saved_point_has_coordinate_ranging(
    aircraft: str, monkeypatch: Any
) -> None:
    """Without CR the aircraft shows EL as asterisks, whatever elevation is written
    (flown, escalation #517)."""
    points = [_point(f"T{n}") for n in range(21, 26)]
    for point, altitude in zip(points, [0, 69, 100, 1234, -100]):
        point.altitude_ft = altitude
    flight = _flight(aircraft=aircraft, route=10, saved=points)

    settings = _database(flight, monkeypatch)

    assert set(settings["waypoints"]) == set(range(10, 15))
    for waypoint, point in zip(settings["waypoints"].values(), points):
        assert waypoint["wpt_cr"] == 1
        assert waypoint["wpt_elev_present"] == 1
        assert waypoint["wpt_elev"] == pytest.approx(point.altitude_ft * 0.3048)
        assert waypoint["wpt_attributes"]["attr_vnav"] == 1


def test_the_saved_points_get_a_flight_plan_of_their_own(monkeypatch: Any) -> None:
    """Plan 1 is the mission route and cannot be overridden -- measured -- so what
    keeps the route clean is the points not being on it."""
    written = _settings(
        _flight(route=5, saved=[_point("SMOKE"), _point("SHIP")]), monkeypatch
    )

    assert '["fp_name"]="EXTRA"' in written
    assert re.findall(r'\["wpt_number"\]=(\d+)', written) == ["5", "6"]


def test_a_flight_with_nothing_written_down_gets_no_plan(monkeypatch: Any) -> None:
    written = _settings(_flight(), monkeypatch)

    assert "flight_plans" not in written
    assert loads(written)["settings"]["waypoints"] == {}


def test_an_orbit_is_not_written(monkeypatch: Any) -> None:
    """The A-10's database has no orbit element; the kind rides on the kneeboard."""
    orbit = SavedPoint(kind=PointKind.ORBIT, name="CAP", x=1.0, y=2.0)

    cdu = _database(_flight(saved=[orbit, _point("OIL")]), monkeypatch)["waypoints"]

    assert [entry["wpt_id"] for entry in cdu.values()] == ["OIL"]


# ------------------------------------------------------------- the numbering


def test_a_saved_point_follows_the_route() -> None:
    """The aircraft numbers a waypoint by its place in the table, not by the wpt_num
    written beside it, and DCS's own route counts from 0."""
    assert a10cdu.numbers_for(5, 2) == [5, 6]
    assert a10cdu.numbers_for(1, 2) == [1, 2]
    assert a10cdu.numbers_for(0, 3) == [1, 2, 3]


@pytest.mark.parametrize("route_length", [0, 1, 3, 8])
def test_the_saved_points_start_where_the_route_ends(
    route_length: int, monkeypatch: Any
) -> None:
    flight = _flight(route=route_length, saved=[_point("OIL"), _point("SHIP")])

    settings = _database(flight, monkeypatch)

    first = max(1, route_length)
    assert list(settings["waypoints"]) == [first, first + 1]
    assert settings["waypoints"][first]["wpt_id"] == "OIL"
    assert settings["waypoints"][first + 1]["wpt_id"] == "SHIP"
    extra = settings["flight_plans"][a10cdu.EXTRA_PLAN]["waypoints"]
    assert [point["wpt_number"] for point in extra.values()] == [first, first + 1]


def test_the_kneeboard_gives_a_point_the_number_the_cdu_does(monkeypatch: Any) -> None:
    from game.ato.dtcoptions import DtcOptions
    from game.missiongenerator.dtc.savedpoints import point_numbers

    flight = _flight(route=6, saved=[_point("OIL"), _point("SHIP")])

    cdu = _database(flight, monkeypatch)["waypoints"]
    numbers = point_numbers(
        "A-10C_2", flight.waypoints, DtcOptions(), flight.saved_points, False, True
    )

    assert numbers == list(cdu) == [6, 7]


def test_the_number_written_is_the_slot(monkeypatch: Any) -> None:
    written = _settings(_flight(route=3, saved=[_point("SMOKE")]), monkeypatch)

    assert re.findall(r'\["wpt_num"\]=(\d+)', written) == ["3"]


# ------------------------------------------------------------------- the names


def test_a_name_is_cut_to_what_the_cdu_shows(monkeypatch: Any) -> None:
    written = _settings(_flight(saved=[_point("A very long name indeed")]), monkeypatch)

    assert '["wpt_id"]="A VERY LONG "' in written


def test_a_point_with_no_usable_name_still_gets_one(monkeypatch: Any) -> None:
    written = _settings(_flight(route=2, saved=[_point("¿¿¿")]), monkeypatch)

    assert '["wpt_id"]="PT2"' in written


# ---------------------------------------------------------------------- VNAV


@pytest.mark.parametrize("aircraft", ["A-10C", "A-10C_2"])
def test_a_player_a10_route_gets_3d_vnav_and_keeps_its_altitudes(
    aircraft: str,
) -> None:
    terrain = Caucasus()
    points = [MovingPoint(Point(n, n, terrain)) for n in range(3)]
    points[0].properties = None  # the spawn point is set as well
    for point in points[1:]:
        point.properties = PointProperties(scale=Scale.Terminal, steer=Steer.Direct)
        point.alt = 4572
        point.alt_type = "BARO"
    flight = SimpleNamespace(
        client_count=1,
        unit_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id=aircraft)),
    )
    before = [(p.alt, p.alt_type) for p in points]

    a10cdu.enable_route_vnav(
        cast(Any, flight), cast(Any, SimpleNamespace(points=points))
    )

    assert [p.dict()["properties"]["vnav"] for p in points] == [1, 1, 1]
    assert [(p.alt, p.alt_type) for p in points] == before
    for point in points[1:]:
        assert point.properties is not None
        assert point.properties.scale is Scale.Terminal
        assert point.properties.steer is Steer.Direct


@pytest.mark.parametrize("aircraft,crewed", [("A-10C_2", 0), ("FA-18C_hornet", 1)])
def test_vnav_is_left_alone_for_ai_and_other_aircraft(
    aircraft: str, crewed: int
) -> None:
    point = MovingPoint(Point(0, 0, Caucasus()))
    point.properties = PointProperties(vnav=VNav.V2D)
    flight = SimpleNamespace(
        client_count=crewed,
        unit_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id=aircraft)),
    )
    before = point.dict()

    a10cdu.enable_route_vnav(
        cast(Any, flight), cast(Any, SimpleNamespace(points=[point]))
    )

    assert point.dict() == before


def test_the_saved_points_and_their_plan_use_3d_vnav(monkeypatch: Any) -> None:
    cdu = _database(_flight(saved=[_point("OIL")]), monkeypatch)

    for waypoint in cdu["waypoints"].values():
        assert waypoint["wpt_attributes"]["attr_vnav"] == 1
    extra = cdu["flight_plans"][a10cdu.EXTRA_PLAN]["waypoints"]
    assert extra[1]["wpt_attributes"]["attr_vnav"] == 1


# ---------------------------------------------------------- into the mission


def test_only_a_crewed_a10_with_points_is_written(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(
        a10cdu,
        "Point",
        lambda x, y, terrain: SimpleNamespace(latlng=lambda: _latlng(x, y)),
    )
    mission = tmp_path / "turn.miz"
    with zipfile.ZipFile(mission, "w") as archive:
        archive.writestr("mission", "-- a mission")
    data = SimpleNamespace(
        flights=[
            _flight(saved=[_point("SMOKE")]),
            _flight(saved=[_point("SHIP")], crewed=0),  # nobody in it
            _flight(),  # nothing written down
            _flight(
                aircraft="FA-18C_hornet", saved=[_point("SMOKE")]
            ),  # has a cartridge
        ]
    )
    game = SimpleNamespace(theater=SimpleNamespace(terrain=_Terrain()))

    written = a10cdu.write_into_mission(cast(Any, game), data, mission)

    assert written == ["Avionics/A-10C_2/7/CDU/SETTINGS.lua"]
    with zipfile.ZipFile(mission) as archive:
        assert archive.read("mission") == b"-- a mission"
        settings = loads(archive.read(written[0]).decode("utf-8"))["settings"]
        assert set(settings["waypoints"]) == {4}
        assert settings["waypoints"][4]["wpt_id"] == "SMOKE"
        assert settings["flight_plans"][a10cdu.EXTRA_PLAN]["fp_name"] == "EXTRA"


def test_nothing_to_write_leaves_the_mission_alone(tmp_path: Path) -> None:
    mission = tmp_path / "turn.miz"
    with zipfile.ZipFile(mission, "w") as archive:
        archive.writestr("mission", "-- a mission")
    game = SimpleNamespace(theater=SimpleNamespace(terrain=_Terrain()))

    assert (
        a10cdu.write_into_mission(cast(Any, game), SimpleNamespace(flights=[]), mission)
        == []
    )

    with zipfile.ZipFile(mission) as archive:
        assert archive.namelist() == ["mission"]
