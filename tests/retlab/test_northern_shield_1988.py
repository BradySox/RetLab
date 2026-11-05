"""Germany - Northern Shield 1988 laydown guards.

Red Tide's war from the north: NATO holds Copenhagen, Sturup and Bornholm across
the water, and the Warsaw Pact holds the East German coast and the Uckermark.

What these pin is what fails silently:

* a red control point without the invert flag stays red in an inverted game;
* a road to a blue base would open a land front the DM ruled out;
* a garrison outside Barth's capture zone lets an air assault take it untouched;
* the SAMs are the template's sites, and the SA-5 must stay inland;
* DCS stands are nested, so a base's slot count is not the constraint.

Design note: docs/dev/design/retlab-northern-shield-1988-campaign-notes.md
"""

import copy
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest
import yaml
from dcs.mission import Mission

from game import persistency
from game.campaignloader.campaign import Campaign
from game.dcs.aircrafttype import AircraftType
from game.factions import FACTIONS
from game.theater import ConflictTheater
from game.theater.controlpoint import TRIGGER_RADIUS_CAPTURE, Airfield
from game.theater.start_generator import ModSettings

YAML = Path("resources/campaigns/northern_shield_1988.yaml")
MIZ = Path("resources/campaigns/northern_shield_1988.miz")

NATO = "Blufor Late Cold War (80s)"
PACT = "Russia 1980 (Red Tide)"
BLUE = {"Kastrup", "Sturup", "Bornholm"}
RED = {"Barth", "Peenemunde", "Neubrandenburg", "Templin"}
ROADS = {
    frozenset(pair)
    for pair in (
        ("Barth", "Peenemunde"),
        ("Barth", "Neubrandenburg"),
        ("Peenemunde", "Neubrandenburg"),
        ("Neubrandenburg", "Templin"),
    )
}
LANES = {
    frozenset(pair)
    for pair in (
        ("Kastrup", "Sturup"),
        ("Kastrup", "Bornholm"),
        ("Kastrup", "Barth"),
        ("Bornholm", "Peenemunde"),
    )
}


def _preset_types() -> dict[str, str]:
    """Squadron preset name -> aircraft type, the first file to claim a name."""
    presets: dict[str, str] = {}
    for path in Path("resources/squadrons").rglob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        presets.setdefault(str(data["name"]), str(data["aircraft"]))
    return presets


def _miz() -> Mission:
    mission = Mission()
    mission.load_file(str(MIZ))
    return mission


@pytest.fixture(scope="module")
def loaded(tmp_path_factory: Any) -> tuple[Campaign, ConflictTheater]:
    persistency.setup(str(tmp_path_factory.mktemp("northern-shield-1988")), False, 0)
    campaign = Campaign.from_file(YAML)
    return campaign, campaign.load_theater(campaign.advanced_iads)


def test_the_date_and_sides(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    start = campaign.recommended_start_date
    assert start is not None
    assert (start.year, start.month) == (1988, 7)
    assert campaign.recommended_player_faction == NATO
    assert campaign.recommended_enemy_faction == PACT


def test_every_squadron_is_stock_dcs(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """Red Tide's NATO faction lists mod jets; no squadron here flies one."""
    presets = _preset_types()
    campaign, theater = loaded
    stock = {}
    for name in (NATO, PACT):
        faction = copy.deepcopy(FACTIONS[name])
        faction.apply_mod_settings(ModSettings.all_off())
        # ``all_aircrafts`` is cached; read the stripped sets directly.
        kept = set(faction.aircraft) | set(faction.awacs) | set(faction.tankers)
        stock[name] = {a.display_name for a in kept}
    config = campaign.load_air_wing_config(theater)
    for cp, squadrons in config.by_location.items():
        side = NATO if cp.starting_coalition.is_blue else PACT
        for squadron in squadrons:
            (named,) = squadron.aircraft
            kind = AircraftType.named(presets.get(named, named)).display_name
            assert kind in stock[side], f"{cp.name}: {kind} needs a mod"


def test_who_holds_what(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    blue = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_blue}
    red = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_red}
    assert blue == BLUE
    assert red == RED
    assert len(theater.controlpoints) == len(BLUE) + len(RED)
    assert all(isinstance(cp, Airfield) for cp in theater.controlpoints)


def test_every_red_point_inverts_and_no_blue_one_does(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    for cp in theater.controlpoints:
        assert cp.captured_invert is cp.starting_coalition.is_red, cp.name


def test_no_land_front_until_a_red_base_falls(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    roads = set()
    lanes = set()
    for cp in theater.controlpoints:
        roads |= {frozenset((cp.name, other.name)) for other in cp.connected_points}
        lanes |= {frozenset((cp.name, other.name)) for other in cp.shipping_lanes}
    assert roads == ROADS
    assert lanes == LANES
    for name in BLUE:
        assert theater.control_point_named(name).is_isolated, name
    # Every road joins two red bases: no front line until one changes hands.
    assert all(pair <= RED for pair in roads)


def test_garrisons_hold_the_capture_zones(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """Barth's garrison must be cleared before an air assault takes it, and each
    NATO field keeps one so a red air assault cannot take it unopposed."""
    _, theater = loaded
    for name in ("Barth", "Kastrup", "Sturup", "Bornholm"):
        cp = theater.control_point_named(name)
        garrisons = [
            p
            for p in cp.preset_locations.armor_groups
            if p.original_name == f"NS88-{name}-Garrison"
        ]
        assert len(garrisons) == 1, name
        # Well inside, so the garrison's units are too.
        assert garrisons[0].distance_to_point(cp.position) < 2800, name


def test_the_sams_are_the_templates_and_the_sa5_is_inland(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """Carsten's framework sites, unit by unit; no SA-10; one SA-5, in the rear."""
    campaign, theater = loaded
    fixed = {
        site.original_name: cp
        for cp in theater.controlpoints
        for site in cp.preset_locations.exact_air_defenses
    }
    assert len(fixed) == 18
    hawks = {name for name in fixed if name.startswith("FIXED Hawk ")}
    assert {fixed[name].name for name in hawks} == {"Kastrup"}
    for name, cp in fixed.items():
        assert cp.starting_coalition.is_blue is (name in hawks), (name, cp.name)
    assert [name for name in fixed if "SA-5" in name] == ["FIXED SA-5 Badingen"]
    assert fixed["FIXED SA-5 Badingen"].name == "Templin"
    # The generated sites are the mobile ones, each pinned.
    pins = campaign.data["ground_forces"]
    generated = {
        p.original_name
        for cp in theater.controlpoints
        for p in cp.preset_locations.medium_range_sams
        + cp.preset_locations.long_range_sams
    }
    assert generated == set(pins)
    assert set(pins.values()) == {"Hawk", "SA-6", "SA-11"}
    mission = _miz()
    kinds = {
        unit.type
        for country in mission.coalition["red"].countries.values()
        for group in country.vehicle_group
        for unit in group.units
    }
    assert not any("S-300" in kind for kind in kinds)


def test_the_neighbours_take_sides(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    pinned = {z.country: z.posture_override for z in theater.neutral_border_zones}
    for country in ("Germany", "Sweden"):
        assert pinned[country] == "blue", country
    for country in ("Poland", "Czech Republic"):
        assert pinned[country] == "red", country


def test_no_base_oversubscribes_a_stand_class(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """Hall's condition over the nested stand classes (see test_iron_gate)."""
    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    presets = _preset_types()
    for cp, squadrons in config.by_location.items():
        assert isinstance(cp, Airfield), cp.name
        airport = cp.airport
        wanted: dict[int, int] = defaultdict(int)
        for squadron in squadrons:
            (named,) = squadron.aircraft
            aircraft = AircraftType.named(presets.get(named, named))
            if aircraft.helicopter:
                continue
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


def test_every_squadron_flies_a_type_in_its_sides_faction(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    presets = _preset_types()
    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    rosters = {True: FACTIONS[NATO], False: FACTIONS[PACT]}
    for cp, squadrons in config.by_location.items():
        fielded = {
            a.display_name for a in rosters[cp.starting_coalition.is_blue].all_aircrafts
        }
        for squadron in squadrons:
            (named,) = squadron.aircraft
            kind = AircraftType.named(presets.get(named, named)).display_name
            assert kind in fielded, f"{cp.name}: the faction has no {kind}"


def test_bornholm_carries_the_air_assault(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    bornholm = theater.control_point_named("Bornholm")
    tasks = {s.primary.value for s in config.by_location[bornholm]}
    assert tasks == {"Air Assault"}


def test_the_soviet_iads_net() -> None:
    statics = [
        group.units[0].type
        for country in _miz().coalition["red"].countries.values()
        for group in country.static_group
        if group.name.startswith("NS88-IADS-")
    ]
    assert statics.count(".Command Center") == 2
    assert statics.count("Comms tower M") == 8
    assert statics.count("GeneratorF") == 3


def test_every_road_leaves_its_bases_off_road() -> None:
    """An On Road first leg the editor cannot path crashes it (dcs.log, 2026-10-20)."""
    roads = [
        group
        for country in _miz().coalition["blue"].countries.values()
        for group in country.vehicle_group
        if group.units[0].type == "M-113"
    ]
    assert len(roads) == len(ROADS)
    for group in roads:
        assert group.points[0].action.value == "Off Road", group.name
        assert group.points[-1].action.value == "Off Road", group.name
        assert all(p.action.value == "On Road" for p in group.points[1:-1]), group.name


def test_the_nordbahn(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    barth = theater.control_point_named("Barth")
    assert [cp.name for cp in barth.rail_lines] == ["Neubrandenburg"]
