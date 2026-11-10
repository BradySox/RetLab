"""Civilian air traffic planning and spawning (Python side).

Rebuilt 2026-11-09 to the DM's picks: real civil types only, a steady stream switched
on by the ``civtraffic`` plugin, routes clear of the fronts and every known SAM ring,
and an Off / Light / Normal / Busy level. The plugin is covered in
``tests/lua/test_civtraffic_runtime.py``.
"""

from __future__ import annotations

import random
from typing import Any

import dcs
import pytest
from dcs.mapping import Point
from dcs.planes import C_130, IL_76MD, An_30M
from dcs.terrain import Caucasus
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon

from game.missiongenerator.civilianfleet import (
    ALL_TYPES,
    AN_26,
    CIVIL_TRAFFIC_NONE,
    MI_8,
    REGIONS,
    YAK_40,
    YAK_52,
    CivilRegion,
    region_for,
)
from game.missiongenerator.civiliantraffic import (
    AIRWAY,
    CRUISE_EXIT_FRAC,
    FRONT_KEEPOUT_M,
    HOP,
    HOP_MAX_M,
    MIN_TRANSIT_M,
    NAVAL_SPEED_MS,
    NAVAL_TYPES,
    SAM_MARGIN_M,
    TARGETS,
    CivilField,
    CivilFlight,
    CivilianTrafficGenerator,
    NavalCivilianTrafficGenerator,
    NavalRoute,
    airway_routes,
    along,
    clear_of,
    cruise_points,
    edge_gates,
    hop_routes,
    max_age_s,
    plan_airways,
    plan_hops,
    war_airspace,
)
from game.settings.enums import CivilAirTraffic

_T = None  # terrain only passed through; never dereferenced in planning
NM = 1_852


def _pt(x: float, y: float) -> Point:
    return Point(x, y, _T)  # type: ignore[arg-type]  # terrain never dereferenced


def _field(
    name: str, x: float, y: float, runway: bool = True, elevation: float = 100
) -> CivilField:
    return CivilField(name, _pt(x, y), has_runway=runway, elevation_m=elevation)


_NO_WAR = war_airspace([], [])
_REGION = CivilRegion(airliners=(YAK_40,), local=(MI_8,), operators=("AEROFLOT",))


# --- what flies ---------------------------------------------------------------


def test_no_military_transport_flies_as_civil_traffic() -> None:
    """The IL-76 read as military on radar; Red Tide M1 lost one to a Phoenix."""
    flown = {t.aircraft for t in ALL_TYPES}
    assert not flown & {IL_76MD, C_130, An_30M}


def test_the_an26_flies_only_on_the_ex_soviet_maps() -> None:
    """DM call 2026-11-09: Caucasus, Kola, Afghanistan and Syria."""
    with_an26 = {name for name, r in REGIONS.items() if AN_26 in r.airliners}
    assert with_an26 == {"Caucasus", "Kola", "Afghanistan", "Syria"}


def test_every_mapped_modern_theater_flies_the_yak40() -> None:
    for name, region in REGIONS.items():
        if region is not CIVIL_TRAFFIC_NONE:
            assert YAK_40 in region.airliners, name


def test_the_1944_maps_have_no_civil_traffic() -> None:
    for name in ("Normandy", "TheChannel", "MarianaIslandsWWII"):
        assert region_for(name) is CIVIL_TRAFFIC_NONE


def test_a_type_not_yet_in_service_does_not_fly() -> None:
    early = region_for("Caucasus").for_year(1968)
    assert YAK_40 in early.airliners
    assert AN_26 not in early.airliners  # 1969
    assert YAK_52 not in early.local  # 1979
    assert not region_for("Caucasus").for_year(1960).airliners


def test_an_unknown_map_falls_back_rather_than_generating_nothing() -> None:
    assert region_for("SomeFutureTerrain").airliners


def test_every_region_key_is_a_real_terrain_name() -> None:
    """A typo'd key fails silently into the fallback. The campaign yamls carry display
    names ("Persian Gulf"); this table is keyed on ``Terrain.name`` ("PersianGulf")."""
    import inspect

    import dcs.terrain as terrain_module
    from dcs.terrain.terrain import Terrain

    real = set()
    for _, obj in inspect.getmembers(terrain_module, inspect.isclass):
        if issubclass(obj, Terrain) and obj is not Terrain:
            try:
                real.add(obj().name)  # type: ignore[call-arg]
            except Exception:  # pragma: no cover - a terrain that needs an install
                continue
    unknown = set(REGIONS) - real
    assert not unknown, f"not real Terrain.name values: {sorted(unknown)}"


def test_every_airliner_is_fast_enough_to_air_start() -> None:
    """An air start below ~190 kt at altitude fell out of the sky (2026-08-08)."""
    for civil_type in ALL_TYPES:
        if not civil_type.agl:
            assert civil_type.speed_ms >= 100, civil_type.aircraft.id


def test_every_type_has_a_civil_paint() -> None:
    for civil_type in ALL_TYPES:
        assert civil_type.liveries, civil_type.aircraft.id


def test_the_levels_get_busier() -> None:
    totals = [sum(TARGETS[level]) for level in CivilAirTraffic]
    assert totals == sorted(totals)
    assert TARGETS[CivilAirTraffic.OFF] == (0, 0)
    assert 4 <= sum(TARGETS[CivilAirTraffic.LIGHT]) <= 6


# --- where it flies -----------------------------------------------------------


def test_a_leg_through_the_front_is_refused() -> None:
    war = war_airspace([_pt(0, 0)], [])
    assert not clear_of(_pt(-200_000, 0), _pt(200_000, 0), war)
    beside = FRONT_KEEPOUT_M + 5_000
    assert clear_of(_pt(-200_000, beside), _pt(200_000, beside), war)


def test_a_leg_through_a_sam_ring_is_refused() -> None:
    ring = ShapelyPoint(0, 0).buffer(20 * NM)
    war = war_airspace([], [ring])
    assert not clear_of(_pt(-200_000, 0), _pt(200_000, 0), war)
    just_outside_ring = 20 * NM + SAM_MARGIN_M / 2
    assert not clear_of(
        _pt(-200_000, just_outside_ring), _pt(200_000, just_outside_ring), war
    ), "the margin keeps traffic off the very edge of the ring"
    clear = 20 * NM + SAM_MARGIN_M + 2_000
    assert clear_of(_pt(-200_000, clear), _pt(200_000, clear), war)


def test_a_union_of_rings_is_refused_too() -> None:
    box = Polygon([(-1_000, -1_000), (1_000, -1_000), (1_000, 1_000), (-1_000, 1_000)])
    war = war_airspace([], [box])
    assert not clear_of(_pt(-50_000, 0), _pt(50_000, 0), war)


def test_edge_gates_sit_on_the_airfield_box() -> None:
    gates = edge_gates([_pt(0, 0), _pt(400_000, 300_000), _pt(100_000, 50_000)])
    assert len(gates) == 24
    for g in gates:
        assert g.x in (0, 400_000) or g.y in (0, 300_000)
        assert 0 <= g.x <= 400_000 and 0 <= g.y <= 300_000


def test_airways_are_long_and_flown_both_ways() -> None:
    fields = [_field("A", 0, 0), _field("B", 300_000, 0), _field("C", 50_000, 0)]
    routes = airway_routes(fields, [], _NO_WAR)
    names = {(a[0].name, b[0].name) for a, b in routes if a[0] and b[0]}
    assert ("A", "B") in names and ("B", "A") in names
    assert ("A", "C") not in names  # 50 km is a hop, not an airway
    for (_, a), (_, b) in routes:
        assert a.distance_to_point(b) >= MIN_TRANSIT_M


def test_an_airliner_never_uses_a_helipad() -> None:
    """Test 59: an An-26 and an IL-76 sent to Syria's helipads crashed."""
    fields = [_field("A", 0, 0), _field("Pad", 300_000, 0, runway=False)]
    assert airway_routes(fields, [], _NO_WAR) == []


def test_two_gates_on_one_edge_are_not_an_airway() -> None:
    gates = [_pt(500_000, 0), _pt(500_000, 400_000)]  # both on the north edge
    assert airway_routes([], gates, _NO_WAR) == []


def test_a_leg_into_the_war_is_never_an_airway() -> None:
    war = war_airspace([_pt(300_000, 0)], [])
    fields = [_field("A", 0, 0), _field("Front", 300_000, 0)]
    assert airway_routes(fields, [], war) == []


def test_hops_stay_short_and_clear() -> None:
    fields = [_field("A", 0, 0), _field("B", 60_000, 0), _field("Far", 400_000, 0)]
    routes = hop_routes(fields, _NO_WAR)
    for a, b in routes:
        assert a.point.distance_to_point(b.point) <= HOP_MAX_M
    assert {(a.name, b.name) for a, b in routes} == {("A", "B"), ("B", "A")}


# --- the steady stream --------------------------------------------------------


def _airway_routes() -> list[Any]:
    fields = [_field("A", 0, 0), _field("B", 300_000, 0)]
    gates = edge_gates([_pt(0, -200_000), _pt(400_000, 200_000)])
    return airway_routes(fields, gates, _NO_WAR)


def test_the_target_count_is_flying_at_mission_start() -> None:
    flights = plan_airways(_airway_routes(), _REGION, 4, random.Random(1))
    live = [f for f in flights if f.live]
    assert len(live) == 4
    assert all(f.air_start for f in live), "live airliners are already en route"


def test_the_queue_covers_the_mission() -> None:
    flights = plan_airways(
        _airway_routes(), _REGION, 4, random.Random(2), cover_s=3 * 3_600
    )
    queued = [f for f in flights if not f.live]
    assert sum(f.duration_s for f in queued) >= 4 * 3 * 3_600
    assert all(f.layer == AIRWAY for f in flights)


def test_a_queued_airliner_enters_at_the_edge_or_departs_a_field() -> None:
    """No more pop-ins mid-map: a switched-on flight starts at a gate or a runway."""
    flights = plan_airways(_airway_routes(), _REGION, 4, random.Random(3))
    for f in flights:
        if f.live:
            continue
        if f.origin is None:
            assert f.air_start_point == f.start
        else:
            assert f.air_start_point is None


def test_nothing_departs_a_high_field() -> None:
    """Test 40: an IL-76 out of Bamyan hit the valley 88 s after takeoff."""
    fields = [_field("High", 0, 0, elevation=2_565), _field("Low", 300_000, 0)]
    routes = airway_routes(fields, [], _NO_WAR)
    flights = plan_airways(routes, _REGION, 2, random.Random(4))
    assert flights
    assert all(f.origin is None or f.origin.name != "High" for f in flights)


def test_hops_that_start_together_leave_from_different_fields() -> None:
    fields = [_field(chr(65 + i), i * 40_000, 0) for i in range(4)]
    flights = plan_hops(hop_routes(fields, _NO_WAR), _REGION, 3, random.Random(5))
    live = [f for f in flights if f.live]
    assert len(live) == 3
    assert len({f.origin.name for f in live if f.origin}) == 3
    assert all(f.layer == HOP for f in flights)


def test_a_light_plane_never_hops_to_a_helipad() -> None:
    region = CivilRegion(airliners=(), local=(YAK_52,), operators=("DOSAAF",))
    fields = [_field("A", 0, 0), _field("Pad", 40_000, 0, runway=False)]
    assert plan_hops(hop_routes(fields, _NO_WAR), region, 1, random.Random(6)) == []


def test_nothing_is_planned_at_zero_target_or_with_no_routes() -> None:
    assert plan_airways(_airway_routes(), _REGION, 0, random.Random(7)) == []
    assert plan_airways([], _REGION, 4, random.Random(7)) == []
    assert plan_airways(_airway_routes(), CIVIL_TRAFFIC_NONE, 4, random.Random(7)) == []


def test_every_flight_carries_an_operator_callsign() -> None:
    flights = plan_airways(_airway_routes(), _REGION, 4, random.Random(8))
    assert all(f.callsign.startswith("AEROFLOT ") for f in flights)


# --- the cruise level ---------------------------------------------------------


def _flight(**overrides: Any) -> CivilFlight:
    a, b = _field("A", 0, 0), _field("B", 300_000, 0)
    kwargs: dict[str, Any] = dict(
        civil_type=YAK_40,
        layer=AIRWAY,
        origin=a,
        destination=b,
        start=a.point,
        end=b.point,
        live=False,
        air_start_point=None,
        callsign="AEROFLOT 412",
        livery="Aeroflot",
        duration_s=3_000,
    )
    kwargs.update(overrides)
    return CivilFlight(**kwargs)


def test_a_field_to_field_flight_climbs_then_descends() -> None:
    """Without a level waypoint DCS flew a shallow V and never climbed (2026-08-08)."""
    points = cruise_points(_flight())
    assert len(points) == 2
    assert points[1].x == pytest.approx(300_000 * CRUISE_EXIT_FRAC)


def test_a_live_flight_takes_only_the_points_still_ahead() -> None:
    flight = _flight(air_start_point=_pt(150_000, 0), live=True)
    points = cruise_points(flight)
    assert [p.x for p in points] == [pytest.approx(300_000 * CRUISE_EXIT_FRAC)]


def test_a_map_edge_exit_has_no_descent() -> None:
    assert len(cruise_points(_flight(destination=None))) == 1  # top of climb only


def test_a_stuck_flight_is_given_time_to_finish_first() -> None:
    assert max_age_s(_flight()) > 3_000


# --- what lands in the .miz ---------------------------------------------------


def _caucasus() -> tuple[Any, Any, list[CivilField]]:
    mission = dcs.mission.Mission(terrain=Caucasus())
    country = mission.country("Russia")
    names = list(mission.terrain.airports)
    fields = [
        CivilField(name, mission.terrain.airports[name].position)
        for name in (names[0], names[-1])
    ]
    return mission, country, fields


def _miz_flight(fields: list[CivilField], **overrides: Any) -> CivilFlight:
    a, b = fields
    kwargs: dict[str, Any] = dict(
        civil_type=AN_26,
        layer=AIRWAY,
        origin=a,
        destination=b,
        start=a.point,
        end=b.point,
        live=False,
        air_start_point=None,
        callsign="AEROFLOT 412",
        livery="Aeroflot",
        duration_s=3_000,
    )
    kwargs.update(overrides)
    return CivilFlight(**kwargs)


def test_a_queued_flight_waits_switched_off() -> None:
    mission, country, fields = _caucasus()
    generator = CivilianTrafficGenerator(mission, None)  # type: ignore[arg-type]
    name = generator._spawn(country, 0, _miz_flight(fields))
    assert name == "AEROFLOT 412 [0]"
    group = country.plane_group[-1]
    assert group.late_activation is True
    assert group.units[0].livery_id == "aeroflot"


def test_a_departure_climbs_to_its_level_and_lands() -> None:
    mission, country, fields = _caucasus()
    generator = CivilianTrafficGenerator(mission, None)  # type: ignore[arg-type]
    generator._spawn(country, 0, _miz_flight(fields))
    group = country.plane_group[-1]
    assert len(group.points) == 4  # takeoff, top of climb, top of descent, land
    for waypoint in group.points[1:3]:
        assert waypoint.alt == AN_26.altitude_m
        assert waypoint.speed == pytest.approx(AN_26.speed_ms)
    assert group.points[-1].type == "Land"


def test_a_live_airliner_spawns_at_its_cruise_speed() -> None:
    """The stall: DCS takes the air-start velocity from the unit record, in m/s, and
    pydcs takes km/h. Passing m/s spawned the old fleet at a third of cruise."""
    mission, country, fields = _caucasus()
    mid = along(fields[0].point, fields[1].point, 0.5)
    flight = _miz_flight(fields, live=True, air_start_point=mid, civil_type=YAK_40)
    generator = CivilianTrafficGenerator(mission, None)  # type: ignore[arg-type]
    generator._spawn(country, 0, flight)
    group = country.plane_group[-1]
    assert group.late_activation is False
    assert group.units[0].speed == pytest.approx(YAK_40.speed_ms)
    assert group.units[0].alt == YAK_40.altitude_m


def test_an_edge_exit_ends_on_its_gate_at_cruise() -> None:
    mission, country, fields = _caucasus()
    gate = Point(fields[1].point.x + 50_000, fields[1].point.y, mission.terrain)
    flight = _miz_flight(fields, destination=None, end=gate)
    generator = CivilianTrafficGenerator(mission, None)  # type: ignore[arg-type]
    generator._spawn(country, 0, flight)
    last = country.plane_group[-1].points[-1]
    assert (last.position.x, last.position.y) == (gate.x, gate.y)
    assert last.alt == AN_26.altitude_m


def test_a_hop_flies_low_over_the_ground() -> None:
    mission, country, fields = _caucasus()
    flight = _miz_flight(fields, civil_type=MI_8, layer=HOP)
    generator = CivilianTrafficGenerator(mission, None)  # type: ignore[arg-type]
    generator._spawn(country, 0, flight)
    group = country.helicopter_group[-1]
    assert group.points[1].alt_type == "RADIO"
    assert group.points[1].speed == pytest.approx(MI_8.speed_ms)


def test_ambient_boats_make_way_at_their_hull_speed() -> None:
    mission = dcs.mission.Mission(terrain=Caucasus())
    country = mission.country("Russia")
    route = NavalRoute(
        ship_type=NAVAL_TYPES[0],
        chain=(Point(0.0, 0.0, mission.terrain), Point(1_000.0, 0.0, mission.terrain)),
    )
    generator = NavalCivilianTrafficGenerator(mission, None)  # type: ignore[arg-type]
    assert generator._spawn(country, 0, route) is True
    assert country.ship_group[-1].points[-1].speed == pytest.approx(NAVAL_SPEED_MS)


# --- what the plugin is handed ------------------------------------------------


def test_the_plugin_node_carries_targets_and_flights() -> None:
    from types import SimpleNamespace

    from game.missiongenerator.civiliantraffic import (
        CivilTrafficLua,
        CivilTrafficLuaFlight,
    )
    from game.missiongenerator.civiltrafficluadata import populate_civil_traffic_lua
    from game.missiongenerator.luagenerator import LuaData

    plan = CivilTrafficLua(targets={AIRWAY: 4, HOP: 1})
    plan.flights.append(
        CivilTrafficLuaFlight(
            "AEROFLOT 412 [0]", AIRWAY, True, (1_000.4, -2_000.6), "Batumi", 5_000
        )
    )
    root = LuaData("dcsRetribution")
    populate_civil_traffic_lua(root, SimpleNamespace(civil_traffic=plan))  # type: ignore[arg-type]
    lua = root.create_operations_lua()
    for expected in (
        'airway = "4"',
        'hop = "1"',
        'group = "AEROFLOT 412 [0]"',
        'queued = "true"',
        'exitX = "1000"',
        'exitZ = "-2001"',
        'field = "Batumi"',
        'maxAge = "5000"',
    ):
        assert expected in lua, expected


def test_nothing_reaches_the_plugin_when_off() -> None:
    from types import SimpleNamespace

    from game.missiongenerator.civiltrafficluadata import populate_civil_traffic_lua
    from game.missiongenerator.luagenerator import LuaData

    root = LuaData("dcsRetribution")
    populate_civil_traffic_lua(root, SimpleNamespace(civil_traffic=None))  # type: ignore[arg-type]
    assert root.get_item("civilTraffic") is None
