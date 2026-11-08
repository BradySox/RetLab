"""Persian Gulf - Eastern Reach 2025 laydown guards.

A fictional 2025 war: the Marines hold Bandar-e-Jask and drive up the
Minab-Kahnuj-Jiroft highway to Kerman. The .miz is the DM's Mission Editor
save; edit it there.

What these pin is what fails silently:

* a road that skips a FOB, or one to Lar or Bandar Abbas, changes the front the
  campaign is built around;
* a red control point without the invert flag stays red in an inverted game;
* a squadron pinned to a type its faction does not field is quietly swapped;
* a mod box left unticked drops the Bavar-373, the 3rd Khordad, the missile
  launchers and the F-15EX at New Game;
* the UAE template batteries must stay FIXED, or New Game makes stock sites.

Design note: docs/dev/design/retlab-eastern-reach-campaign-notes.md
"""

import copy
from collections import defaultdict
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest
from dcs.mission import Mission

from game import persistency
from game.campaignloader.campaign import Campaign
from game.dcs.aircrafttype import AircraftType
from game.factions import FACTIONS
from game.theater import ConflictTheater, ParkingType
from game.theater.airfieldclearance import airfield_clearance_conflicts
from game.theater.controlpoint import Airfield
from game.theater.start_generator import ModSettings

YAML = Path("resources/campaigns/eastern_reach_2025.yaml")
MIZ = Path("resources/campaigns/eastern_reach_2025.miz")

BLUE_FACTION = "USA 2020"
RED_FACTION = "[CH] Iran 2025"
BLUE = {
    "Al Dhafra AFB",
    "Al Minhad AFB",
    "Al Ain Intl",
    "Fujairah Intl",
    "Bandar-e-Jask",
    "ER-CVN",
    "ER-LHA",
}
RED = {
    "FOB Sirik",
    "FOB Minab",
    "FOB Kahnuj",
    "Jiroft",
    "FOB Jebal Barez",
    "Kerman",
    "Lar",
}
HIGHWAY = (
    "Bandar-e-Jask",
    "FOB Sirik",
    "FOB Minab",
    "FOB Kahnuj",
    "Jiroft",
    "FOB Jebal Barez",
    "Kerman",
)
UAE_SITES = {
    "FIXED Al Dhafra Patriot",
    "FIXED Al Dhafra Hawk",
    "FIXED Al Minhad Patriot",
    "FIXED Fujairah EWR",
}


@pytest.fixture(scope="module")
def loaded(tmp_path_factory: Any) -> tuple[Campaign, ConflictTheater]:
    persistency.setup(str(tmp_path_factory.mktemp("eastern-reach")), False, 0)
    campaign = Campaign.from_file(YAML)
    return campaign, campaign.load_theater(campaign.advanced_iads)


def test_the_date(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    start = campaign.recommended_start_date
    assert start is not None
    assert start.year == 2025


def test_new_game_ticks_every_mod(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    for mod in (
        "iranmilitaryassetspack",
        "iranairdefensepack",
        "usamilitaryassetspack",
        "f15ex_v3",
        "fa_18efg",
        "f22_raptor",
        "uh_60l",
    ):
        assert campaign.settings[mod] is True, mod


def test_who_holds_what(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    blue = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_blue}
    red = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_red}
    assert blue == BLUE
    assert red == RED
    # Bandar Abbas, Havadarya and the rest of the coast are out of the war.
    assert len(theater.controlpoints) == len(blue) + len(red)


def test_every_red_point_inverts_and_no_blue_one_does(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    for cp in theater.controlpoints:
        if cp.name in RED - {"FOB Sirik", "FOB Minab", "FOB Kahnuj", "FOB Jebal Barez"}:
            assert cp.captured_invert, cp.name
        if cp.starting_coalition.is_blue:
            assert not cp.captured_invert, cp.name


def test_the_roads_are_the_highway(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    roads = set()
    for cp in theater.controlpoints:
        roads |= {frozenset((cp.name, other.name)) for other in cp.connected_points}
    assert roads == {frozenset(pair) for pair in zip(HIGHWAY, HIGHWAY[1:])}
    assert not theater.control_point_named("Lar").connected_points


def test_the_range_cap_reaches_kerman_from_al_dhafra(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    campaign, theater = loaded
    distance = (
        theater.control_point_named("Al Dhafra AFB").position.distance_to_point(
            theater.control_point_named("Kerman").position
        )
        / 1852
    )
    assert distance < campaign.settings["max_mission_range_planes"]


def test_the_victory_rules(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    victory = campaign.data["victory"]
    assert victory["win_when"][0]["capture_cps"] == ["Kerman"]
    assert victory["lose_when"][0]["lose_cps"] == ["Bandar-e-Jask"]


def test_every_squadron_flies_a_type_its_side_fields(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """With only the campaign's own mod boxes ticked, as New Game does.

    A type the ticked mods do not provide is swapped at New Game with no log
    line: unticked Super Hornets came out as F-14Bs and F-22s as AH-1Ws (2026-11-07).
    """
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
            kind = AircraftType.named(
                squadron.aircraft_type or squadron.aircraft[0]
            ).display_name
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
            aircraft = AircraftType.named(
                squadron.aircraft_type or squadron.aircraft[0]
            )
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


def test_the_uae_batteries_stay_as_drawn() -> None:
    mission = Mission()
    mission.load_file(str(MIZ))
    groups = {
        group.name: group
        for coalition in mission.coalition.values()
        for country in coalition.countries.values()
        for group in country.vehicle_group
    }
    for name in UAE_SITES:
        assert name in groups, name
        assert len(groups[name].units) > 1, name


def test_al_dhafra_reaches_every_missile_site(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """The deep missile country north of Kerman is in range of the bombers' field."""
    campaign, theater = loaded
    dhafra = theater.control_point_named("Al Dhafra AFB").position
    sites = [
        site
        for cp in theater.controlpoints
        if cp.starting_coalition.is_red
        for site in cp.preset_locations.missile_sites
    ]
    # Kerman 2, Jiroft 1, Bashagard 1, and six north of Kerman (2026-11-07).
    assert len(sites) == 10
    farthest = max(site.distance_to_point(dhafra) for site in sites) / 1852
    assert farthest < campaign.settings["max_mission_range_planes"]
