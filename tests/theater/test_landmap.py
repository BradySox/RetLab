import os
from pathlib import Path

from dcs.mapping import Point
from shapely.geometry import MultiPolygon, Polygon

from dcs.terrain.caucasus.caucasus import Caucasus
from game.theater import landmap
from game.theater.conflicttheater import ConflictTheater
from game.theater.landmap import poly_contains


def _pt(*, x: float, y: float) -> Point:
    # is_on_land/is_in_sea only read .x/.y, so terrain can be None.
    return Point(x, y, None)  # type: ignore[arg-type]


def test_miz() -> None:
    """
    Test miz generation and loading
    """
    test_map = landmap.Landmap(
        inclusion_zones=MultiPolygon([Polygon([(0, 0), (0, 1), (1, 0)])]),
        exclusion_zones=MultiPolygon([Polygon([(1, 1), (0, 1), (1, 0)])]),
        sea_zones=MultiPolygon([Polygon([(0, 0), (0, 2), (1, 0)])]),
    )
    test_filename = "test.miz"
    landmap.to_miz(test_map, Caucasus(), test_filename)
    assert os.path.isfile("test.miz")
    loaded_map = landmap.from_miz("test.miz")
    assert test_map.inclusion_zones.equals_exact(
        loaded_map.inclusion_zones, tolerance=1e-6
    )
    assert test_map.sea_zones.equals_exact(loaded_map.sea_zones, tolerance=1e-6)
    assert test_map.exclusion_zones.equals_exact(
        loaded_map.exclusion_zones, tolerance=1e-6
    )

    if os.path.isfile(test_filename):
        os.remove(test_filename)


def _theater_with(lm: landmap.Landmap) -> ConflictTheater:
    # is_on_land / is_in_sea only touch self.landmap (and each other), so a bare
    # instance with the landmap set is enough to exercise them.
    theater = ConflictTheater.__new__(ConflictTheater)
    theater.landmap = lm
    return theater


def test_is_on_land_and_in_sea_with_multiple_zones() -> None:
    """The terrain queries test the whole prepared MultiPolygon, not per-geom; with
    MULTIPLE exclusion/sea polygons the result must still match a brute-force scan."""
    # Inclusion: one big land square 0..10. Two separate exclusion holes inside it.
    # Two separate sea squares outside the land.
    lm = landmap.Landmap(
        inclusion_zones=MultiPolygon([Polygon([(0, 0), (0, 10), (10, 10), (10, 0)])]),
        exclusion_zones=MultiPolygon(
            [
                Polygon([(1, 1), (1, 3), (3, 3), (3, 1)]),
                Polygon([(6, 6), (6, 8), (8, 8), (8, 6)]),
            ]
        ),
        sea_zones=MultiPolygon(
            [
                Polygon([(20, 20), (20, 22), (22, 22), (22, 20)]),
                Polygon([(30, 30), (30, 32), (32, 32), (32, 30)]),
            ]
        ),
    )
    theater = _theater_with(lm)

    def ref_on_land(x: float, y: float) -> bool:
        if not poly_contains(x, y, lm.inclusion_zones):
            return False
        return not any(poly_contains(x, y, g) for g in lm.exclusion_zones.geoms)

    def ref_in_sea(x: float, y: float) -> bool:
        if ref_on_land(x, y):
            return False
        if any(poly_contains(x, y, g) for g in lm.exclusion_zones.geoms):
            return False
        return any(poly_contains(x, y, g) for g in lm.sea_zones.geoms)

    # Spot checks across land, both exclusion holes, and both sea squares.
    cases = [(5, 5), (2, 2), (7, 7), (21, 21), (31, 31), (-5, -5), (5, 0.5)]
    for x, y in cases:
        pt = _pt(x=float(x), y=float(y))
        assert theater.is_on_land(pt) == ref_on_land(x, y), (x, y, "on_land")
        assert theater.is_in_sea(pt) == ref_in_sea(x, y), (x, y, "in_sea")

    # The headline cases, explicitly.
    assert theater.is_on_land(_pt(x=5.0, y=5.0)) is True
    assert theater.is_on_land(_pt(x=2.0, y=2.0)) is False  # exclusion hole 1
    assert theater.is_on_land(_pt(x=7.0, y=7.0)) is False  # exclusion hole 2
    assert theater.is_in_sea(_pt(x=21.0, y=21.0)) is True  # sea square 1
    assert theater.is_in_sea(_pt(x=31.0, y=31.0)) is True  # sea square 2
    assert theater.is_in_sea(_pt(x=5.0, y=5.0)) is False  # on land


def test_load_landmap_rebuilds_prepared_index(tmp_path: Path) -> None:
    """Pickle bypasses __post_init__; load_landmap must re-prepare so queries are
    indexed (and correct) after a load."""
    import pickle

    lm = landmap.Landmap(
        inclusion_zones=MultiPolygon([Polygon([(0, 0), (0, 4), (4, 4), (4, 0)])]),
        exclusion_zones=MultiPolygon([Polygon([(1, 1), (1, 2), (2, 2), (2, 1)])]),
        sea_zones=MultiPolygon([Polygon([(8, 8), (8, 9), (9, 9), (9, 8)])]),
    )
    path = tmp_path / "lm.pkl"
    with open(path, "wb") as f:
        pickle.dump(lm, f)

    loaded = landmap.load_landmap(path)
    assert loaded is not None
    theater = _theater_with(loaded)
    assert theater.is_on_land(_pt(x=3.0, y=3.0)) is True
    assert theater.is_on_land(_pt(x=1.5, y=1.5)) is False
    assert theater.is_in_sea(_pt(x=8.5, y=8.5)) is True


def test_poly_contains_survives_concurrent_first_queries() -> None:
    """The map server answers requests on several threads; two of them querying
    a freshly prepared zone set at once crashed the app on save load (GEOS
    access violation). Without the lock this kills the test process."""
    import random
    import threading

    import shapely as shp

    for _ in range(10):
        squares = [
            Polygon([(i * 10, j * 10), (i * 10 + 8, j * 10), (i * 10 + 8, j * 10 + 8)])
            for i in range(40)
            for j in range(40)
        ]
        zones = MultiPolygon(squares)
        shp.prepare(zones)
        barrier = threading.Barrier(8)

        def query() -> None:
            barrier.wait()
            for _ in range(1000):
                poly_contains(random.uniform(0, 400), random.uniform(0, 400), zones)

        threads = [threading.Thread(target=query) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
