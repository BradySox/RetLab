"""Falklands - Mount Pleasant 2032 laydown guards.

A fictional November 2032 war: Argentina has landed at Goose Green and San Carlos,
the UK garrison and a US detachment hold Mount Pleasant and Stanley, and the war
ends when the islands are clear. Built from the map by
``tools/build_mount_pleasant_2032_miz.py``.

What these pin is what fails silently:

* a red control point without the invert flag stays red in an inverted game;
* a road from the islands to the mainland would let the front reach a field the
  campaign promises can never be taken;
* DCS stands are nested, so a base's slot count is not the constraint;
* the blue side needs the CurrentHill UK pack and the red side the A-4E, and a
  mod unit dropped at New Game takes its squadron with it.

Design note: docs/dev/design/retlab-mount-pleasant-2032-campaign-notes.md
"""

import copy
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest
import yaml

from game import persistency
from game.campaignloader.campaign import Campaign
from game.dcs.aircrafttype import AircraftType
from game.factions import FACTIONS
from game.theater import ConflictTheater, ParkingType
from game.theater.controlpoint import Airfield
from game.theater.start_generator import ModSettings

YAML = Path("resources/campaigns/mount_pleasant_2032.yaml")

BLUE_FACTION = "UK-US Falklands Garrison 2032"
RED_FACTION = "Argentina 2032"
BLUE = {"Mount Pleasant", "Port Stanley", "Ascension Island"}
ISLANDS_RED = {"Goose Green", "San Carlos FOB"}
MAINLAND = {"Rio Gallegos", "Rio Grande", "San Julian", "Ushuaia"}
ROADS = {
    frozenset(pair)
    for pair in (
        ("Mount Pleasant", "Goose Green"),
        ("Mount Pleasant", "Port Stanley"),
        ("Port Stanley", "San Carlos FOB"),
        ("Goose Green", "San Carlos FOB"),
        ("Rio Gallegos", "San Julian"),
        ("Rio Grande", "Ushuaia"),
    )
}


@pytest.fixture(scope="module")
def loaded(tmp_path_factory: Any) -> tuple[Campaign, ConflictTheater]:
    persistency.setup(str(tmp_path_factory.mktemp("mount-pleasant-2032")), False, 0)
    campaign = Campaign.from_file(YAML)
    return campaign, campaign.load_theater(campaign.advanced_iads)


def test_the_date(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    start = campaign.recommended_start_date
    assert start is not None
    # Southern spring.
    assert (start.year, start.month) == (2032, 11)


def test_each_side_needs_only_its_named_mod(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), False, 0)
    blue = copy.deepcopy(FACTIONS[BLUE_FACTION])
    aircraft = {a.display_name for a in blue.aircraft}
    presets = {g.name for g in blue.preset_groups}
    blue.apply_mod_settings(ModSettings())
    assert {a.display_name for a in blue.aircraft} == aircraft
    # Without the CurrentHill UK pack only its Sky Sabre and Stormer go.
    assert presets - {g.name for g in blue.preset_groups} == {
        "Sky Sabre Battery",
        "Stormer HVM Battery",
    }

    red = copy.deepcopy(FACTIONS[RED_FACTION])
    aircraft = {a.display_name for a in red.aircraft}
    red.apply_mod_settings(ModSettings())
    assert aircraft - {a.display_name for a in red.aircraft} == {"A-4E Skyhawk"}


def test_new_game_ticks_both_mods(loaded: tuple[Campaign, ConflictTheater]) -> None:
    """The campaign's settings pre-tick the New Game mod boxes it needs."""
    campaign, _ = loaded
    assert campaign.settings["ukmilitaryassetspack"] is True
    assert campaign.settings["a4_skyhawk"] is True


def test_who_holds_what(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    blue = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_blue}
    red = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_red}
    assert blue == BLUE
    assert red == ISLANDS_RED | MAINLAND
    assert len(theater.controlpoints) == len(blue) + len(red)


def test_every_red_point_inverts_and_no_blue_one_does(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    for cp in theater.controlpoints:
        assert cp.captured_invert is cp.starting_coalition.is_red, cp.name


def test_the_mainland_has_no_road_to_the_islands(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    roads = set()
    for cp in theater.controlpoints:
        roads |= {frozenset((cp.name, other.name)) for other in cp.connected_points}
    assert roads == ROADS
    for pair in roads:
        assert len(pair & MAINLAND) in (0, 2), pair
    opposed = {
        pair
        for pair in ROADS
        if len(
            {theater.control_point_named(n).starting_coalition.is_blue for n in pair}
        )
        == 2
    }
    assert opposed == {
        frozenset(("Mount Pleasant", "Goose Green")),
        frozenset(("Port Stanley", "San Carlos FOB")),
    }


def test_the_range_cap_reaches_every_island_field(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    campaign, theater = loaded
    cap = campaign.settings["max_mission_range_planes"]
    for field in MAINLAND:
        for target in ("Mount Pleasant", "Port Stanley"):
            distance = (
                theater.control_point_named(field).position.distance_to_point(
                    theater.control_point_named(target).position
                )
                / 1852
            )
            assert distance < cap, (field, target)


def test_the_victory_rules(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    victory = campaign.data["victory"]
    assert set(victory["win_when"][0]["capture_cps"]) == ISLANDS_RED
    assert victory["lose_when"][0]["lose_cps"] == ["Mount Pleasant"]


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


def test_every_squadron_is_a_named_unit_in_its_sides_faction(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    presets: dict[str, set[str]] = defaultdict(set)
    for path in Path("resources/squadrons").rglob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data and "name" in data and "aircraft" in data:
            presets[str(data["name"])].add(str(data["aircraft"]))

    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    rosters = {True: FACTIONS[BLUE_FACTION], False: FACTIONS[RED_FACTION]}
    for cp, squadrons in config.by_location.items():
        fielded = {
            a.display_name for a in rosters[cp.starting_coalition.is_blue].all_aircrafts
        }
        for squadron in squadrons:
            kind = squadron.aircraft_type
            assert kind in fielded, f"{cp.name}: the faction has no {kind}"
            (named,) = squadron.aircraft
            assert kind in presets[named], f"{cp.name}: {named!r} flies no {kind}"
