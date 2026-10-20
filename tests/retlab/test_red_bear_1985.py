"""Afghanistan - Red Bear 1985 laydown guards.

A fictional winter war across the top of the Afghanistan map: the USAF holds Herat
and Shindand, the Soviet 40th Army holds the north and Kabul, and the south is out
of play. The .miz is the DM's hand laydown (no build tool).

What these pin is what fails silently:

* a red control point without the invert flag stays red in an inverted game;
* a road drawn to the wrong control point moves a front line;
* both factions are stock DCS, so the campaign needs no mod box ticked;
* DCS stands are nested, so a base's slot count is not the constraint.

Design note: docs/dev/design/retlab-red-bear-1985-campaign-notes.md
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
from game.theater import ConflictTheater, ParkingType
from game.theater.controlpoint import Airfield, Fob, OffMapSpawn
from game.theater.start_generator import ModSettings

YAML = Path("resources/campaigns/red_bear_1985.yaml")
MIZ = Path("resources/campaigns/red_bear_1985.miz")

USAF = "USAF 1985"
USSR = "USSR 40th Army 1985"
MAYMANA = "Maymana Zahiraddin Faryabi"
BLUE = {"Herat", "Shindand", "Camp Bastion"}
RED = {
    "Qala i Naw",
    MAYMANA,
    "Mazar-i-Sharif",
    "Pul-i-Khumri",
    "Chaghcharan",
    "Bamyan",
    "Bagram",
    "Kabul",
    "Jalalabad",
    "Termez",
}
ROADS = {
    frozenset(pair)
    for pair in (
        ("Shindand", "Herat"),
        ("Herat", "Qala i Naw"),
        ("Qala i Naw", MAYMANA),
        (MAYMANA, "Mazar-i-Sharif"),
        ("Mazar-i-Sharif", "Pul-i-Khumri"),
        ("Pul-i-Khumri", "Bagram"),
        ("Herat", "Chaghcharan"),
        ("Chaghcharan", "Bamyan"),
        ("Bamyan", "Kabul"),
        ("Kabul", "Bagram"),
        ("Kabul", "Jalalabad"),
    )
}


def _preset_types() -> dict[str, str]:
    """Squadron preset name -> aircraft type, the first file to claim a name."""
    presets: dict[str, str] = {}
    for path in Path("resources/squadrons").rglob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        presets.setdefault(str(data["name"]), str(data["aircraft"]))
    return presets


@pytest.fixture(scope="module")
def loaded(tmp_path_factory: Any) -> tuple[Campaign, ConflictTheater]:
    persistency.setup(str(tmp_path_factory.mktemp("red-bear-1985")), False, 0)
    campaign = Campaign.from_file(YAML)
    return campaign, campaign.load_theater(campaign.advanced_iads)


def test_the_date(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    start = campaign.recommended_start_date
    assert start is not None
    # Winter, by the DM's call.
    assert (start.year, start.month) == (1985, 1)


def test_both_factions_are_stock(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), False, 0)
    for name in (USAF, USSR):
        faction = copy.deepcopy(FACTIONS[name])
        # ``all_aircrafts`` is cached; the stripped set is ``aircraft``.
        before = {a.display_name for a in faction.aircraft}
        faction.apply_mod_settings(ModSettings.all_off())
        assert {a.display_name for a in faction.aircraft} == before, name
    # The F-100D left the Guard in 1979.
    assert "F-100D Super Sabre" not in {a.display_name for a in FACTIONS[USAF].aircraft}


def test_who_holds_what(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    blue = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_blue}
    red = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_red}
    assert blue == BLUE
    assert red == RED
    # The rest of the south holds nothing.
    assert len(theater.controlpoints) == len(BLUE) + len(RED)
    assert {cp.name for cp in theater.controlpoints if isinstance(cp, Fob)} == {
        "Mazar-i-Sharif",
        "Pul-i-Khumri",
    }
    assert isinstance(theater.control_point_named("Termez"), OffMapSpawn)
    # The heavies' rear is on the map, and no road joins it to the war.
    assert not theater.control_point_named("Camp Bastion").connected_points


def test_every_red_point_inverts_and_no_blue_one_does(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    for cp in theater.controlpoints:
        assert cp.captured_invert is cp.starting_coalition.is_red, cp.name


def test_the_roads(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    roads = set()
    for cp in theater.controlpoints:
        roads |= {frozenset((cp.name, other.name)) for other in cp.connected_points}
    assert roads == ROADS
    opposed = {
        pair
        for pair in ROADS
        if len(
            {theater.control_point_named(n).starting_coalition.is_blue for n in pair}
        )
        == 2
    }
    # The two axes out of Herat: north to Qala i Naw, east up the Hari Rud.
    assert opposed == {
        frozenset(("Herat", "Qala i Naw")),
        frozenset(("Herat", "Chaghcharan")),
    }


def test_the_victory_rules(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    victory = campaign.data["victory"]
    assert victory["win_when"][0]["capture_cps"] == ["Bagram", "Kabul"]
    assert victory["lose_when"][0]["lose_cps"] == ["Herat"]


def test_no_base_oversubscribes_a_stand_class(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """Hall's condition over the nested stand classes (see test_iron_gate)."""
    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    presets = _preset_types()
    for cp, squadrons in config.by_location.items():
        if not isinstance(cp, Airfield):
            if isinstance(cp, OffMapSpawn):
                continue
            pool = cp.total_aircraft_parking(
                ParkingType(fixed_wing=True, fixed_wing_stol=True, rotary_wing=True)
            )
            assert sum(s.max_size for s in squadrons) <= pool, cp.name
            continue
        airport = cp.airport
        wanted: dict[int, int] = defaultdict(int)
        for squadron in squadrons:
            (named,) = squadron.aircraft
            aircraft = AircraftType.named(presets.get(named, named))
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
    rosters = {True: FACTIONS[USAF], False: FACTIONS[USSR]}
    phantoms = 0
    for cp, squadrons in config.by_location.items():
        fielded = {
            a.display_name for a in rosters[cp.starting_coalition.is_blue].all_aircrafts
        }
        for squadron in squadrons:
            (named,) = squadron.aircraft
            kind = presets.get(named, named)
            assert kind in fielded, f"{cp.name}: the faction has no {kind}"
            if kind == "F-4E-45MC Phantom II":
                phantoms += squadron.max_size
    # The campaign exists to fly the Phantom: four squadrons.
    assert phantoms == 44


def test_the_laydown_keeps_its_flavor() -> None:
    """The DM's hand laydown plus the scenery lifted from the Starfire campaigns."""
    mission = Mission()
    mission.load_file(str(MIZ))
    names = set()
    types = set()
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            for group in (
                list(country.vehicle_group)
                + list(country.static_group)
                + list(country.plane_group)
            ):
                names.add(group.name)
                types.add(group.units[0].type)
    assert {
        "Mazar-i-Sharif",
        "Pul-i-Khumri",
        "Termez",
        "RB85-Kabul-Scud",
        "RB85-Bastion-Hawk",
        "RB85 Road Pul-i-Khumri - Bagram (Salang)",
    } <= names
    # An AAV7 is no marker the loader reads; the DM's three are armor now.
    assert "AAV7" not in types
    zones = {zone.name for zone in mission.triggers.zones()}
    assert {"Salma Dam Turbine", "Kabul Ammo Depot Office", "Malan Bridge"} <= zones
    assert not any(name.startswith("Parwan Police") for name in zones)


def test_the_soviet_iads_net(loaded: tuple[Campaign, ConflictTheater]) -> None:
    """Skynet in range mode: two HQs, comms towers and power on real places."""
    campaign, _ = loaded
    assert campaign.advanced_iads
    mission = Mission()
    mission.load_file(str(MIZ))
    statics = [
        group.units[0].type
        for country in mission.coalition["red"].countries.values()
        for group in country.static_group
        if group.name.startswith("RB85-IADS-")
    ]
    assert statics.count(".Command Center") == 2
    assert statics.count("Comms tower M") == 14
    assert statics.count("GeneratorF") == 10
    # One SA-5 guards Kabul and Bagram; the faction's only long-range preset.
    sa5 = [
        group
        for country in mission.coalition["red"].countries.values()
        for group in country.vehicle_group
        if group.units[0].type == "S-300PS 5P85C ln"
    ]
    assert [group.name for group in sa5] == ["RB85-Shomali-SA5"]
    # Blue's Hawks fight on their own: no node is blue.
    for country in mission.coalition["blue"].countries.values():
        assert not any(g.name.startswith("RB85-IADS-") for g in country.static_group)


def test_every_scenery_set_loads(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    # Sixteen sets: ten from Graveyard of Empires, six from Clash of the Titans.
    assert sum(len(cp.preset_locations.scenery) for cp in theater.controlpoints) == 16
    salma = next(
        cp
        for cp in theater.controlpoints
        for group in cp.preset_locations.scenery
        if any(zone.name == "Salma Dam Turbine" for zone in group.zones)
    )
    # The dam is red's, a target on the central axis.
    assert salma.starting_coalition.is_red


def test_every_road_leaves_its_bases_off_road() -> None:
    """An On Road first leg the editor cannot path crashes it (dcs.log, 2026-10-20)."""
    mission = Mission()
    mission.load_file(str(MIZ))
    roads = [
        group
        for country in mission.coalition["blue"].countries.values()
        for group in country.vehicle_group
        if group.units[0].type == "M-113"
    ]
    assert len(roads) == len(ROADS)
    for group in roads:
        assert group.points[0].action.value == "Off Road", group.name
        assert group.points[-1].action.value == "Off Road", group.name
