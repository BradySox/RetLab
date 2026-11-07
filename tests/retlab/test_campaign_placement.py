"""The placement tool: the DCS check script, its reader, and placement by job."""

from __future__ import annotations

import math
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from dcs.terrain import Caucasus

from tests.lua.harness import DcsPluginHarness
from tools.campaign_placement import (
    Job,
    Marker,
    NeedsCheck,
    Placer,
    Reading,
    ReadingCache,
    airfield_problem,
    candidates,
    parse_probe_output,
    point_id,
    probe_config,
    write_review_map,
)

PROBE = "resources/plugins/base/dcs_placement_probe.lua"


def _run_probe(tmp_path: Path, points: list[tuple[float, float]]) -> Path:
    harness = DcsPluginHarness()
    lua = harness.lua
    # A plane rising 1 m every 10 m north, a road east of y = 500, one building
    # 20 m north of every spot.
    lua.execute(
        "land.getHeight = function(p) return p.x / 10 end\n"
        "land.getSurfaceType = function(p) if p.y > 500 then return 4 end return 1 end\n"
        "world.VolumeType = { SPHERE = 2 }\n"
        "Object = Object or {}\nObject.Category = Object.Category or {}\n"
        "Object.Category.SCENERY = 5\n"
        "world.searchObjects = function(cat, vol, handler)\n"
        "  local c = vol.params.point\n"
        "  handler({ getPoint = function() return { x = c.x + 20, y = 0, z = c.z } end,\n"
        "            getTypeName = function() return 'GARAGE A' end })\n"
        "end"
    )
    lua.execute(probe_config("Unit Test", points))
    (tmp_path / "Logs").mkdir()
    lua.globals().lfs = harness.to_lua({})
    lua.execute(f"lfs.writedir = function() return {str(tmp_path) + '/'!r} end")
    harness.load_plugin_script(PROBE)
    harness.advance_to(60.0)
    return tmp_path / "Logs\\retlab_placement_Unit_Test.txt"


def test_the_check_script_writes_what_the_reader_reads(tmp_path: Path) -> None:
    output = _run_probe(tmp_path, [(1000.0, 0.0), (2000.0, 600.0)])
    name, readings = parse_probe_output(output)
    assert name == "Unit_Test"
    flat = readings[point_id(1000.0, 0.0)]
    assert flat.height_m == 100.0
    assert flat.slope_deg == pytest.approx(math.degrees(math.atan(0.1)), abs=0.1)
    assert flat.surface == 1
    assert flat.buildings == 1
    assert flat.nearest_building_m == 20.0
    assert flat.building_type == "GARAGE_A"
    assert readings[point_id(2000.0, 600.0)].surface == 4


def test_a_check_that_did_not_finish_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "out.txt"
    path.write_text("RETLAB-PLACEMENT 1 x 2\n0_0 1 1 1 0 -1 -\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_probe_output(path)


def test_problems_name_slope_water_roads_and_buildings() -> None:
    assert Reading(10, 2, 1, 0, -1, "-").problems() == []
    assert Reading(10, 7, 1, 0, -1, "-").problems() == ["slope 7 deg"]
    assert Reading(10, 0, 3, 0, -1, "-").problems() == ["water"]
    assert Reading(10, 0, 4, 0, -1, "-").problems() == ["road"]
    assert Reading(10, 0, 1, 1, 20, "HOUSE").problems() == [
        "building 66 ft away (HOUSE)"
    ]
    assert Reading(10, 0, 1, 1, 40, "HOUSE").problems() == []


def _airport() -> Any:
    return SimpleNamespace(
        name="Test Field",
        position=SimpleNamespace(x=0.0, y=0.0),
        runways=[SimpleNamespace(heading=0)],
        parking_slots=[SimpleNamespace(position=SimpleNamespace(x=0.0, y=600.0))],
    )


def test_the_runway_strip_and_stands_are_flagged() -> None:
    field = [_airport()]
    assert airfield_problem(field, 1000.0, 100.0) == "Test Field runway strip"
    assert airfield_problem(field, 0.0, 650.0) == "Test Field parking stand"
    assert airfield_problem(field, 2500.0, 100.0) is None


def test_air_defense_sits_under_both_approaches() -> None:
    spots = candidates(Job.AIR_DEFENSE, 0.0, 0.0, _airport())
    first = spots[0]
    assert abs(first.y) < 1.0 and abs(first.x) == pytest.approx(2400.0)
    assert {c.tag for c in spots} == {"0a", "0b"}
    assert all(airfield_problem([_airport()], c.x, c.y) is None for c in spots)


def _placer(tmp_path: Path) -> Placer:
    terrain = Caucasus()
    placer = Placer(terrain, "unit test", ReadingCache("Caucasus", tmp_path))
    placer.airports = []
    return placer


def _fill(placer: Placer, reading: Any) -> None:
    for x, y in placer.unread():
        placer.cache.readings[point_id(x, y)] = reading(x, y)


def test_the_first_build_asks_for_a_check_mission(tmp_path: Path) -> None:
    placer = _placer(tmp_path)
    placer.request("depot", Job.DEPOT, 0.0, 0.0)
    with pytest.raises(NeedsCheck) as raised:
        placer.resolve(check_dir=tmp_path)
    assert raised.value.count == len(candidates(Job.DEPOT, 0.0, 0.0))
    with zipfile.ZipFile(raised.value.path) as miz:
        assert "RETLAB_PLACEMENT" in miz.read("mission").decode("utf-8")


def test_a_steep_spot_is_passed_over(tmp_path: Path) -> None:
    placer = _placer(tmp_path)
    placer.request("depot", Job.DEPOT, 0.0, 0.0)
    best = candidates(Job.DEPOT, 0.0, 0.0)[0]

    def reading(x: float, y: float) -> Reading:
        steep = point_id(x, y) == point_id(best.x, best.y)
        return Reading(100, 12 if steep else 1, 1, 0, -1, "-")

    _fill(placer, reading)
    placement = placer.resolve(check_dir=tmp_path)["depot"]
    assert (placement.x, placement.y) != (best.x, best.y)
    assert placement.skipped == ["slope 12 deg"]


def test_the_ewr_takes_the_high_ground_and_spreads_out(tmp_path: Path) -> None:
    placer = _placer(tmp_path)
    placer.request("ewr 1", Job.EWR, 0.0, 0.0)
    placer.request("ewr 2", Job.EWR, 0.0, 0.0)
    _fill(placer, lambda x, y: Reading(x / 10 + y / 100, 1, 1, 0, -1, "-"))
    picks = placer.resolve(check_dir=tmp_path)
    one, two = picks["ewr 1"], picks["ewr 2"]
    assert one.x == 12000.0 and one.y == 0.0
    assert one.x is not None and one.y is not None
    assert two.x is not None and two.y is not None
    assert math.hypot(one.x - two.x, one.y - two.y) >= 2000.0


def test_the_review_map_escapes_names(tmp_path: Path) -> None:
    page = write_review_map(
        tmp_path / "map.html",
        "t",
        "s",
        [Marker(1.0, 2.0, "<SAM>", ["slope 7 deg"], "flagged")],
    )
    text = page.read_text(encoding="utf-8")
    assert "&lt;SAM&gt;" in text and "<SAM>" not in text
