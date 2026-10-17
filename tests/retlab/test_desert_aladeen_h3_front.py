"""Iraq - Desert Aladeen: The H-3 Front laydown guards.

Starfire's Desert Aladeen with the sides reversed, built from his miz by
``tools/build_desert_aladeen_h3_miz.py``; the original still ships unchanged.

What these pin is what fails silently:

* a squadron whose airframe is not in its faction substitutes without a word,
  and one that needs a mod is dropped, and this campaign promises stock units;
* the H-3 strips have no heavy stands, so a re-based tanker never spawns;
* markers bind the nearest control point, so a moved FOB or a lost influence
  zone hands the Al-Qaim complex to the first rung, and taking it wipes them;
* the DM asked for 75-100 mi between the sides at the start;
* a squadron whose primary its airframe cannot fly never gets that task;
* Kharg has no road or sea link, so only the victory block lets blue win;
* a rear spawn inside a neutral border is engaged by §98's border defense;
* a SAM marker too near a town or the sea puts launchers in it.

Validated at ``load_theater`` depth, the fork's campaign-test convention.
Design note: docs/dev/design/retlab-desert-aladeen-h3-campaign-notes.md
"""

import copy
import importlib.util
import math
from collections import defaultdict
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from dcs.mapping import Point
from dcs.mission import Mission
from shapely.geometry import Point as ShapelyPoint, Polygon
from shapely.strtree import STRtree

from game import persistency
from game.campaignloader.campaign import Campaign
from game.data.groups import GroupTask
from game.dcs.aircrafttype import AircraftType
from game.factions import FACTIONS
from game.retlab.victory import authored_victory_for, parse_victory
from game.theater import ConflictTheater
from game.theater.start_generator import ModSettings

YAML = Path("resources/campaigns/desert_aladeen_h3_front.yaml")
MIZ = Path("resources/campaigns/desert_aladeen_h3_front.miz")
STARFIRE = Path("resources/campaigns/operation_desert_aladeen.yaml")
TOOL = Path("tools/build_desert_aladeen_h3_miz.py")

REAR = "Coalition Rear (Jordan)"
FOB = "FOB Wadi Hauran"
BLUE = {"H-3 Main Airbase", "H-3 Northwest Airbase", "H-3 Southwest Airbase", REAR}
RED = {
    "Kirkuk International Airport",
    "Erbil International Airport",
    "Qayyarah Airfield West",
    "Sulaimaniyah International Airport",
    "Baghdad International Airport",
    "Al-Salam Airbase",
    "Al-Sahra Airport",
    "Mosul International Airport",
    "Al-Kut Airport",
    "Al-Asad Airbase",
    "Al-Taquddum Airport",
    "Kharg Airfield",
    FOB,
}
#: Starfire's two neutral FOBs, left as he authored them.
NEUTRAL = {"FARP Hamrin", "FARP Adhaim"}
METERS_PER_MILE = 1609.344
#: Marker prefix -> the SAM band its layouts come from.
SAM_BANDS = {
    "PATRIOT": GroupTask.LORAD,
    "LORAD": GroupTask.LORAD,
    "NASAMS": GroupTask.MERAD,
    "MERAD": GroupTask.MERAD,
    "SHORAD": GroupTask.SHORAD,
}


@pytest.fixture(scope="module")
def loaded(tmp_path_factory: Any) -> tuple[Campaign, ConflictTheater]:
    persistency.setup(str(tmp_path_factory.mktemp("h3-front")), False, 0)
    campaign = Campaign.from_file(YAML)
    return campaign, campaign.load_theater(campaign.advanced_iads)


def _tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_h3_front", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_it_is_its_own_campaign_and_starfires_is_untouched(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    campaign, _ = loaded
    assert campaign.name == "Iraq - Desert Aladeen - The H-3 Front"
    assert campaign.is_compatible
    source = Campaign.from_file(STARFIRE)
    assert source.name == "Iraq - Operation Desert Aladeen"
    assert source.recommended_player_faction == "USA 2020"
    assert source.recommended_enemy_faction == "Republic of Wadiya 2010"
    original = Mission()
    original.load_file(str(STARFIRE.with_suffix(".miz")))
    blue = {a.name for a in original.terrain.airport_list() if a.is_blue()}
    assert blue == {"Baghdad International Airport", "Al-Salam Airbase"}


@pytest.mark.parametrize("name", ["USA 2012", "Republic of Wadiya 1991"])
def test_both_factions_are_stock_dcs(name: str, tmp_path: Path) -> None:
    """A mod-gated unit is stripped at New Game, and its squadron with it."""
    persistency.setup(str(tmp_path), False, 0)
    faction = copy.deepcopy(FACTIONS[name])
    aircraft = {a.display_name for a in faction.all_aircrafts}
    presets = {g.name for g in faction.preset_groups}
    faction.apply_mod_settings(ModSettings())  # every mod toggle off
    assert {a.display_name for a in faction.all_aircrafts} == aircraft
    assert {g.name for g in faction.preset_groups} == presets
    for kind in faction.all_aircrafts:
        assert kind.dcs_unit_type.__module__.startswith("dcs."), kind.display_name
    assert not faction.requirements


def test_red_has_modern_stock_sams_and_no_support_assets(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), False, 0)
    red = FACTIONS["Republic of Wadiya 1991"]
    assert not red.awacs and not red.tankers
    assert {g.name for g in red.preset_groups} == {
        "SA-10/S-300PS",
        "SA-5/S-200",
        "SA-11",
        "SA-6",
        "SA-15 SHORAD",
        "SA-19 SHORAD",
    }


def test_the_sides_hold_what_the_dm_gave_them(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    owners: dict[str, set[str]] = defaultdict(set)
    for cp in theater.controlpoints:
        owners[cp.starting_coalition.name].add(cp.name)
    assert owners["BLUE"] == BLUE
    assert owners["RED"] == RED
    assert owners["NEUTRAL"] == NEUTRAL
    assert "H-2 Airbase" not in {cp.name for cp in theater.controlpoints}


def test_the_front_starts_75_to_100_miles_out(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    h3 = theater.control_point_named("H-3 Main Airbase")
    fob = theater.control_point_named(FOB)
    enemies = [cp for cp in h3.connected_points if cp.starting_coalition.is_red]
    assert enemies == [fob]
    gap = h3.position.distance_to_point(fob.position) / METERS_PER_MILE
    assert 75 <= gap <= 100, f"{gap:.0f} mi"
    ladder = [FOB, "Al-Asad Airbase", "Al-Taquddum Airport"]
    for here, there in zip(ladder, ladder[1:]):
        assert theater.control_point_named(there) in (
            theater.control_point_named(here).connected_points
        ), (here, there)


def test_no_base_oversubscribes_a_stand_class(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """Hall's condition over the nested stand classes (see test_iron_gate)."""
    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    for cp, squadrons in config.by_location.items():
        airport = getattr(cp, "airport", None)
        if airport is None:  # the off-map rear air-starts
            assert cp.name == REAR
            continue
        wanted: dict[int, int] = defaultdict(int)
        for squadron in squadrons:
            aircraft = AircraftType.named(
                squadron.aircraft_type or squadron.aircraft[0]
            )
            fits = len(airport.free_parking_slots(aircraft.dcs_unit_type))
            assert fits > 0, f"{cp.name}: no stand takes a {aircraft.display_name}"
            wanted[fits] += squadron.max_size
        assert sum(wanted.values()) <= len(airport.parking_slots), cp.name
        for capacity in sorted(wanted):
            needed = sum(n for fits, n in wanted.items() if fits <= capacity)
            assert needed <= capacity, (
                f"{cp.name}: {needed} aircraft need a stand of class {capacity} "
                f"or smaller, but only {capacity} such stands exist"
            )


def test_every_squadron_is_in_its_sides_faction(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """An airframe missing from the faction does not fail; it substitutes."""
    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    rosters = {
        True: FACTIONS[campaign.recommended_player_faction],
        False: FACTIONS[campaign.recommended_enemy_faction],
    }
    count = 0
    for cp, squadrons in config.by_location.items():
        fielded = {
            a.display_name for a in rosters[cp.starting_coalition.is_blue].all_aircrafts
        }
        for squadron in squadrons:
            kind = AircraftType.named(
                squadron.aircraft_type or squadron.aircraft[0]
            ).display_name
            assert kind in fielded, f"{cp.name}: the faction has no {kind}"
            count += 1
    assert count == 40


def test_every_squadron_can_fly_its_primary(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """A primary the airframe cannot fly is never planned for that squadron."""
    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    for cp, squadrons in config.by_location.items():
        for squadron in squadrons:
            kind = AircraftType.named(squadron.aircraft_type or squadron.aircraft[0])
            assert kind.capable_of(
                squadron.primary
            ), f"{cp.name}: a {kind.display_name} cannot fly {squadron.primary.value}"


def test_blue_wins_on_the_iraqi_bases_and_kharg_does_not_count(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """Kharg has no road or sea link, and the stock win needs zero red bases."""
    campaign, theater = loaded
    profile = parse_victory(yaml.safe_load(YAML.read_text(encoding="utf-8"))["victory"])
    assert profile is not None
    by_name = authored_victory_for(
        SimpleNamespace(campaign_name=campaign.name)  # type: ignore[arg-type]
    )
    assert by_name == profile
    (win,) = profile.win_when
    assert set(win.capture_cps) == RED - {"Kharg Airfield"}
    for name in win.capture_cps:
        assert theater.control_point_named(name).connected_points, name
    kharg = theater.control_point_named("Kharg Airfield")
    assert not kharg.connected_points and not kharg.shipping_lanes
    (lose,) = profile.lose_when
    assert lose.lose_cps == ("H-3 Main Airbase",)


def test_markers_bind_the_base_they_were_placed_for(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    bound: dict[str, str] = {}
    for cp in theater.controlpoints:
        presets = cp.preset_locations
        for group in vars(presets).values():
            for location in group if isinstance(group, list) else []:
                name = getattr(location, "original_name", None)
                if name is not None:
                    bound[name] = cp.name
    for name, _, _ in _tool().BASE_MARKERS:
        if " H-3 " in f" {name} ":
            assert theater.control_point_named(bound[name]).starting_coalition.is_blue
    for name in ("LORAD Al-Qaim", "SCUD Al-Qaim", "STRIKE Al-Qaim Rail Yard"):
        assert bound[name] == "Al-Asad Airbase", name
    fob_owned = {name for name, cp in bound.items() if cp == FOB}
    assert fob_owned == {
        name for name, _, _ in _tool().BASE_MARKERS if "Wadi Hauran" in name
    }


def test_the_miz_is_the_build_tools_output_and_every_marker_is_on_land(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    tool = _tool()
    mission = Mission()
    mission.load_file(str(MIZ))
    placed: dict[str, Point] = {}
    for country in mission.coalition["red"].countries.values():
        for vehicles in country.vehicle_group:
            placed[str(vehicles.name)] = vehicles.position
        for statics in country.static_group:
            placed[str(statics.name)] = statics.position
    markers = tool.BASE_MARKERS + tool.NORTH_WEST_MARKERS
    assert len(tool.NORTH_WEST_MARKERS) == 22
    for name, x, y in markers:
        assert name in placed, f"{name}: re-run {TOOL}"
        assert abs(placed[name].x - x) < 1 and abs(placed[name].y - y) < 1, name
        assert theater.is_on_land(placed[name]), name


def test_the_rear_spawn_is_outside_every_neutral_border(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """Inside Jordan, §98's border defense engaged a spawning C-130J after 180 s.

    §98 derives a country's posture from the fields inside it, so one holding
    fields of both sides is contested and never enforces.
    """
    _, theater = loaded
    rear = theater.control_point_named(REAR).position
    here = ShapelyPoint(rear.x, rear.y)
    inside = {
        zone.country
        for zone in theater.neutral_border_zones
        if len(zone.border) >= 3 and Polygon(zone.border).buffer(0).contains(here)
    }
    assert inside == {"Iraq"}
    iraq = [
        Polygon(zone.border).buffer(0)
        for zone in theater.neutral_border_zones
        if zone.country == "Iraq"
    ]
    sides = {
        cp.starting_coalition.name
        for cp in theater.controlpoints
        if cp.name != REAR
        and any(p.contains(ShapelyPoint(cp.position.x, cp.position.y)) for p in iraq)
    }
    assert {"BLUE", "RED"} <= sides


def _widest_layout_m(task: GroupTask) -> float:
    """Every layout either faction can stand on a marker of this band."""
    widest = 0.0
    for name in ("USA 2012", "Republic of Wadiya 1991"):
        for group in FACTIONS[name].preset_groups:
            if task not in group.tasks:
                continue
            for layout in group.layouts:
                for unit_group in layout.all_unit_groups:
                    for unit in unit_group.layout_units:
                        offset = math.hypot(unit.position.x, unit.position.y)
                        widest = max(widest, offset)
    return widest


def test_every_marker_keeps_the_notes_clearances(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """250 m from exclusion zones (a SAM by its widest layout), clear of airfields.

    A layout turns about its marker, so a SAM marker as far from a town or the
    sea as its widest layout reaches puts no launcher in either.
    """
    _, theater = loaded
    tool = _tool()
    landmap = theater.landmap
    assert landmap is not None
    exclusion = list(landmap.exclusion_zones.geoms)
    sea = list(landmap.sea_zones.geoms)
    exclusion_tree, sea_tree = STRtree(exclusion), STRtree(sea)
    reach = {task: _widest_layout_m(task) for task in set(SAM_BANDS.values())}
    airports = [a.position for a in theater.terrain.airport_list()]
    for name, x, y in tool.BASE_MARKERS + tool.NORTH_WEST_MARKERS:
        here = ShapelyPoint(x, y)
        band = SAM_BANDS.get(name.split()[0])
        needed = max(250.0, reach[band]) if band is not None else 250.0
        town = exclusion[exclusion_tree.nearest(here)].distance(here)
        assert town >= needed, f"{name}: {town:.0f} m from an exclusion zone"
        if band is not None:
            water = sea[sea_tree.nearest(here)].distance(here)
            assert water >= reach[band], f"{name}: {water:.0f} m from the sea"
        field = min(p.distance_to_point(Point(x, y, theater.terrain)) for p in airports)
        assert field >= (1200 if "Kharg" in name else 3500), f"{name}: {field:.0f} m"
