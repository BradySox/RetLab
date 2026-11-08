"""Caucasus - Black Sea Landing 1985 laydown guards.

A fictional 1985 war: NATO holds Batumi and Kobuleti with a carrier offshore and
drives up the coast road and the main highway to Tbilisi.

What these pin is what fails silently:

* a road that skips a FOB, or one to Mozdok, changes the front the campaign is
  built around;
* a red control point without the invert flag stays red in an inverted game;
* a squadron pinned to a type its faction does not field is quietly swapped;
* a long-range SAM marker would put an SA-5 or SA-10 in a campaign kept to the
  SA-2, SA-3, SA-6 and SA-11 (the DM's period call).

Design note: docs/dev/design/retlab-black-sea-landing-1985-campaign-notes.md
"""

import copy
from collections import defaultdict
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from game import persistency
from game.campaignloader.campaign import Campaign
from game.dcs.aircrafttype import AircraftType
from game.factions import FACTIONS
from game.squadrons.squadrondefloader import SquadronDefLoader
from game.theater import ConflictTheater, ParkingType
from game.theater.airfieldclearance import airfield_clearance_conflicts
from game.theater.controlpoint import Airfield
from game.theater.start_generator import ModSettings

YAML = Path("resources/campaigns/black_sea_landing_1985.yaml")

BLUE_FACTION = "Blufor Late Cold War (80s)"
RED_FACTION = "Russia 1980"
BLUE = {"Batumi", "Kobuleti", "BSL-CV", "BSL-LHA"}
FOBS = {"FOB Poti", "FOB Zugdidi", "FOB Zestafoni", "FOB Khashuri", "FOB Gori"}
RED = FOBS | {
    "Senaki-Kolkhi",
    "Kutaisi",
    "Sukhumi-Babushara",
    "Tbilisi-Lochini",
    "Vaziani",
    "Mozdok",
}
HIGHWAY = (
    "Batumi",
    "Kobuleti",
    "FOB Poti",
    "Senaki-Kolkhi",
    "Kutaisi",
    "FOB Zestafoni",
    "FOB Khashuri",
    "FOB Gori",
    "Tbilisi-Lochini",
    "Vaziani",
)
ABKHAZ_COAST = ("Senaki-Kolkhi", "FOB Zugdidi", "Sukhumi-Babushara")


def _type_of(name: str) -> AircraftType:
    """A squadron pin is a preset name first, then an aircraft type (as New Game)."""
    for directory in SquadronDefLoader.squadron_directories():
        for _, squadron_def in SquadronDefLoader.load_squadrons_from(directory):
            if squadron_def.name == name:
                return squadron_def.aircraft
    return AircraftType.named(name)


@pytest.fixture(scope="module")
def loaded(tmp_path_factory: Any) -> tuple[Campaign, ConflictTheater]:
    persistency.setup(str(tmp_path_factory.mktemp("black-sea-landing")), False, 0)
    campaign = Campaign.from_file(YAML)
    return campaign, campaign.load_theater(campaign.advanced_iads)


def test_the_date(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    start = campaign.recommended_start_date
    assert start is not None
    assert start.year == 1985


def test_who_holds_what(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    blue = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_blue}
    red = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_red}
    assert blue == BLUE
    assert red == RED
    # Sochi, Gudauta, Nalchik, Beslan and the Krasnodar fields are out of the war.
    assert len(theater.controlpoints) == len(blue) + len(red)


def test_every_red_field_inverts_and_no_blue_one_does(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    for cp in theater.controlpoints:
        if cp.name in RED - FOBS:
            assert cp.captured_invert, cp.name
        if cp.starting_coalition.is_blue:
            assert not cp.captured_invert, cp.name


def test_the_roads_are_the_highway(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    roads = set()
    for cp in theater.controlpoints:
        roads |= {frozenset((cp.name, other.name)) for other in cp.connected_points}
    expected = {frozenset(pair) for pair in zip(HIGHWAY, HIGHWAY[1:])}
    expected |= {frozenset(pair) for pair in zip(ABKHAZ_COAST, ABKHAZ_COAST[1:])}
    assert roads == expected
    assert not theater.control_point_named("Mozdok").connected_points


def test_the_range_cap_reaches_vaziani_from_kobuleti(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    campaign, theater = loaded
    distance = (
        theater.control_point_named("Kobuleti").position.distance_to_point(
            theater.control_point_named("Vaziani").position
        )
        / 1852
    )
    assert distance < campaign.settings["max_mission_range_planes"]


def test_the_victory_rules(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    victory = campaign.data["victory"]
    assert victory["win_when"][0]["capture_cps"] == ["Tbilisi-Lochini", "Vaziani"]
    assert victory["lose_when"][0]["lose_cps"] == ["Kobuleti"]


def test_no_long_range_sam(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    for cp in theater.controlpoints:
        assert not cp.preset_locations.long_range_sams, cp.name


def test_every_squadron_flies_a_type_its_side_fields(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """With only the campaign's own mod boxes ticked, as New Game does."""
    campaign, theater = loaded
    names = {f.name for f in fields(ModSettings)}
    mods = ModSettings(
        **{k: v for k, v in campaign.settings.items() if k in names and v is True}
    )
    rosters = {}
    for blue, faction_name in ((True, BLUE_FACTION), (False, RED_FACTION)):
        faction = copy.deepcopy(FACTIONS[faction_name])
        faction.apply_mod_settings(mods)
        rosters[blue] = {a.display_name for a in faction.all_aircrafts}
    config = campaign.load_air_wing_config(theater)
    for cp, squadrons in config.by_location.items():
        fielded = rosters[cp.starting_coalition.is_blue]
        for squadron in squadrons:
            kind = _type_of(squadron.aircraft[0]).display_name
            assert kind in fielded, f"{cp.name}: New Game would swap the {kind}"


def test_no_base_oversubscribes_a_stand_class(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """Hall's condition over the nested stand classes (see test_iron_gate)."""
    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    for cp, squadrons in config.by_location.items():
        if not isinstance(cp, Airfield):
            pool = cp.total_aircraft_parking(
                ParkingType(fixed_wing=True, fixed_wing_stol=True, rotary_wing=True)
            )
            assert sum(s.max_size for s in squadrons) <= pool, cp.name
            continue
        airport = cp.airport
        wanted: dict[int, int] = defaultdict(int)
        for squadron in squadrons:
            aircraft = _type_of(squadron.aircraft[0])
            fits = len(airport.free_parking_slots(aircraft.dcs_unit_type))
            assert fits > 0, f"{cp.name}: no stand takes a {aircraft.display_name}"
            wanted[fits] += squadron.max_size
        assert sum(wanted.values()) <= len(airport.parking_slots), cp.name
        for capacity in sorted(wanted):
            needed = sum(n for fits, n in wanted.items() if fits <= capacity)
            assert needed <= capacity, (cp.name, capacity, needed)


def test_nothing_stands_on_a_runway_or_stand(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    assert airfield_clearance_conflicts(theater) == []
