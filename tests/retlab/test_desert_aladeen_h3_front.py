"""Iraq - Desert Aladeen: The H-3 Front laydown guards.

Starfire's Desert Aladeen with the sides reversed, built from his miz by
``tools/build_desert_aladeen_h3_miz.py``; the original still ships unchanged.

What these pin is what fails silently:

* a squadron whose airframe is not in its faction substitutes without a word,
  and one that needs a mod is dropped, and this campaign promises stock units;
* the H-3 strips have no heavy stands, so a re-based tanker never spawns;
* markers bind the nearest control point, so a moved FOB or a lost influence
  zone hands the Al-Qaim complex to the first rung, and taking it wipes them;
* the DM asked for 75-100 mi between the sides at the start.

Validated at ``load_theater`` depth, the fork's campaign-test convention.
Design note: docs/dev/design/retlab-desert-aladeen-h3-campaign-notes.md
"""

import copy
import importlib.util
from collections import defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from dcs.mapping import Point
from dcs.mission import Mission

from game import persistency
from game.campaignloader.campaign import Campaign
from game.dcs.aircrafttype import AircraftType
from game.factions import FACTIONS
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
