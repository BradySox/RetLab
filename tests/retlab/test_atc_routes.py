"""Voice ATC step 2 (§119): the Caucasus chart points and runway matching."""

from __future__ import annotations

from dcs.terrain import Caucasus, Syria

from game.retlab.atc_routes import _chart_file, chart_routes, dcs_runway


def test_every_caucasus_chart_names_a_dcs_airport_and_its_runways() -> None:
    terrain = Caucasus()
    names = list(_chart_file(terrain.name))
    assert len(names) == 20
    for name in names:
        routes = chart_routes(terrain, name)
        assert routes is not None, name
        field = terrain.airports[name].position
        ends = {r.main.name for r in terrain.airports[name].runways} | {
            r.opposite.name for r in terrain.airports[name].runways
        }
        assert any(p.entry_runways for p in routes.points), name
        assert any(p.exit for p in routes.points), name
        for point in routes.points:
            assert set(point.entry_runways) <= ends, (name, point.name)
            # Every chart point sits 3 to 11 NM out.
            assert 3 <= field.distance_to_point(point.position) / 1852 <= 11, (
                name,
                point.name,
            )


def test_kobuleti_black_sea_is_where_the_chart_puts_it() -> None:
    terrain = Caucasus()
    routes = chart_routes(terrain, "Kobuleti")
    assert routes is not None and routes.chart == "VAD 01"
    black_sea = routes.points[0]
    assert black_sea.name == "Black Sea" and black_sea.entry_runways == ("07",)
    field = terrain.airports["Kobuleti"].position
    # The chart's UG5X 7.3 DME arc.
    assert round(field.distance_to_point(black_sea.position) / 1852, 1) == 7.3


def test_a_chart_runway_takes_the_nearest_dcs_end() -> None:
    assert dcs_runway("12", ["13", "31"]) == "13"
    assert dcs_runway("04L", ["05", "23"]) == "05"
    assert dcs_runway("04", ["01", "19"]) == "01"
    assert dcs_runway("02", ["06", "24"]) is None


def test_a_map_without_charts_has_no_routes() -> None:
    assert chart_routes(Syria(), "Incirlik") is None


def test_a_route_leaves_by_the_exit_nearest_its_first_point_past_5_nm() -> None:
    from dcs.mapping import Point

    from game.retlab.atc_routes import FieldRoutes, RoutePoint, planned_exit

    terrain = Caucasus()
    field = Point(0, 0, terrain)
    north = RoutePoint("Lake", Point(13000, 0, terrain), ("23",), True)
    south = RoutePoint("Bravo", Point(-13000, 0, terrain), ("05",), True)
    routes = FieldRoutes("52 TFW SOP", 2600, 2600, (north, south))
    # The first waypoint is the climb-out 2 NM north; the route then heads south.
    waypoints = [Point(3700, 0, terrain), Point(-40000, 5000, terrain)]
    assert planned_exit(routes, field, waypoints) == "Bravo"
    assert planned_exit(routes, field, []) is None


def test_departure_turns_load_and_take_the_dcs_runway(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from game.retlab import atc_routes

    (tmp_path / "caucasus.yaml").write_text(
        """
Kobuleti:
  chart: test
  max_altitude_ft: 2000
  pattern_ft: 1500
  points:
    - {name: Black Sea, lat: "42 01.126", lon: "041 45.124", entry: ["07"], exit: true}
  departure_turns:
    - {runway: "25", turn: right, heading: 280, exits: [Black Sea]}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(atc_routes, "ROUTES_DIR", tmp_path)
    atc_routes._chart_file.cache_clear()
    try:
        routes = chart_routes(Caucasus(), "Kobuleti")
    finally:
        atc_routes._chart_file.cache_clear()
    assert routes is not None
    (turn,) = routes.departure_turns
    assert (turn.runway, turn.direction, turn.heading, turn.exits) == (
        "25",
        "right",
        280,
        ("Black Sea",),
    )
