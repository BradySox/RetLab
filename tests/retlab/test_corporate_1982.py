"""Falklands - Operation Corporate 1982 laydown guards.

The 1982 war from 21 May: the UK holds the San Carlos beachhead and two carriers,
Argentina holds Stanley, Goose Green, Mount Kent and four mainland strike fields,
and Chile is out of it. Built from the map by ``tools/build_corporate_1982_miz.py``.

What these pin is what fails silently:

* a red control point without the invert flag stays red in an inverted game,
  so playing Argentina would hand the player nothing;
* DCS stands are nested, so a base's slot count is not the constraint;
* the Argentine faction needs the A-4E mod and nothing else, and the UK needs
  none;
* a mainland field inside the mission-range cap of a carrier would send the
  Harriers to the mainland, which the 1982 task force never did.

Design note: docs/dev/design/retlab-corporate-1982-campaign-notes.md
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
from game.theater.controlpoint import Airfield, Fob, Lha
from game.theater.start_generator import ModSettings

YAML = Path("resources/campaigns/corporate_1982.yaml")
MIZ = Path("resources/campaigns/corporate_1982.miz")

UK = "UK Falklands Task Force 1982"
ARGENTINA = "Argentina Falklands 1982"
BLUE = {"San Carlos FOB", "HMS Hermes", "HMS Invincible", "Ascension Island"}
RED = {
    "Port Stanley",
    "Goose Green",
    "Mount Kent",
    "Rio Gallegos",
    "Rio Grande",
    "San Julian",
    "Ushuaia",
    "ARA Veinticinco de Mayo",
}
MAINLAND = {"Rio Gallegos", "Rio Grande", "San Julian", "Ushuaia"}
ROADS = {
    frozenset(pair)
    for pair in (
        ("San Carlos FOB", "Goose Green"),
        ("San Carlos FOB", "Mount Kent"),
        ("Mount Kent", "Port Stanley"),
        ("Goose Green", "Port Stanley"),
        ("Rio Gallegos", "San Julian"),
        ("Rio Grande", "Ushuaia"),
    )
}


@pytest.fixture(scope="module")
def loaded(tmp_path_factory: Any) -> tuple[Campaign, ConflictTheater]:
    persistency.setup(str(tmp_path_factory.mktemp("corporate-1982")), False, 0)
    campaign = Campaign.from_file(YAML)
    return campaign, campaign.load_theater(campaign.advanced_iads)


def test_the_date(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    start = campaign.recommended_start_date
    assert start is not None
    # The San Carlos landing.
    assert (start.year, start.month, start.day) == (1982, 5, 21)


def test_the_uk_is_stock_and_argentina_needs_only_the_a4(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), False, 0)
    uk = copy.deepcopy(FACTIONS[UK])
    before = {a.display_name for a in uk.aircraft}
    uk.apply_mod_settings(ModSettings())
    assert {a.display_name for a in uk.aircraft} == before

    argentina = copy.deepcopy(FACTIONS[ARGENTINA])
    # ``all_aircrafts`` is cached; the stripped set is ``aircraft``.
    before = {a.display_name for a in argentina.aircraft}
    ships = {s.display_name for s in argentina.naval_units}
    argentina.apply_mod_settings(ModSettings())
    assert before - {a.display_name for a in argentina.aircraft} == {"A-4E Skyhawk"}
    assert {s.display_name for s in argentina.naval_units} == ships


def test_who_holds_what(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    blue = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_blue}
    red = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_red}
    assert blue == BLUE
    assert red == RED
    # Mount Pleasant (built 1985) and every Chilean field hold nothing.
    assert len(theater.controlpoints) == len(BLUE) + len(RED)
    assert {cp.name for cp in theater.controlpoints if isinstance(cp, Lha)} == {
        "HMS Hermes",
        "HMS Invincible",
    }
    assert isinstance(theater.control_point_named("Mount Kent"), Fob)


def test_every_red_point_inverts_and_no_blue_one_does(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """Invert Sides hands the player every point with the flag, and only those."""
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
    # Two fronts out of the beachhead: south to Goose Green, east to Mount Kent.
    assert opposed == {
        frozenset(("San Carlos FOB", "Goose Green")),
        frozenset(("San Carlos FOB", "Mount Kent")),
    }


def test_the_range_cap_reaches_the_islands_but_not_the_carriers(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    campaign, theater = loaded
    cap = campaign.settings["max_mission_range_planes"]

    def nm(a: str, b: str) -> float:
        return (
            theater.control_point_named(a).position.distance_to_point(
                theater.control_point_named(b).position
            )
            / 1852
        )

    for field in MAINLAND:
        # The strike groups reach Stanley, the farthest island field.
        assert nm(field, "Port Stanley") < cap, field
        for carrier in ("HMS Hermes", "HMS Invincible"):
            # The Harriers never reach the mainland.
            assert nm(field, carrier) > cap, (field, carrier)


def test_the_victory_rules(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    victory = campaign.data["victory"]
    assert victory["win_when"][0]["capture_cps"] == ["Port Stanley"]
    assert victory["lose_when"][0]["lose_cps"] == ["San Carlos FOB"]


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


def test_every_squadron_is_a_1982_unit_in_its_sides_faction(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    presets: dict[str, str] = {}
    for path in Path("resources/squadrons").rglob("*1982.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        presets[str(data["name"])] = str(data["aircraft"])

    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    rosters = {True: FACTIONS[UK], False: FACTIONS[ARGENTINA]}
    count = 0
    for cp, squadrons in config.by_location.items():
        fielded = {
            a.display_name for a in rosters[cp.starting_coalition.is_blue].all_aircrafts
        }
        for squadron in squadrons:
            kind = squadron.aircraft_type
            assert kind in fielded, f"{cp.name}: the faction has no {kind}"
            (named,) = squadron.aircraft
            assert presets.get(named) == kind, f"{cp.name}: {named!r}"
            count += 1
    assert count == len(presets) == 20


def test_the_carriers_sail_the_hulls_the_yaml_names(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    campaign, _ = loaded
    config = campaign.load_carrier_config().by_original_name
    assert config["HMS Hermes"].preferred_type.display_name == "LHA-1 Tarawa"
    assert config["HMS Invincible"].preferred_type.display_name == "R05 Invincible"
    assert config["ARA Veinticinco de Mayo"].preferred_type.display_name == (
        "ARA Veinticinco de Mayo"
    )
    # The preferred hull is honoured only if the faction's DCS country may sail it.
    from dcs.countries import country_dict

    for faction, hulls in (
        (FACTIONS[UK], {"LHA_Tarawa", "hms_invincible"}),
        (FACTIONS[ARGENTINA], {"ara_vdm"}),
    ):
        allowed = {
            v.id
            for k, v in country_dict[faction.country.id].Ship.__dict__.items()  # type: ignore
            if "__" not in k
        }
        assert hulls <= allowed, faction.name


def test_the_miz_matches_the_tool() -> None:
    mission = Mission()
    mission.load_file(str(MIZ))
    names = set()
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            for group in (
                list(country.vehicle_group)
                + list(country.ship_group)
                + list(country.static_group)
                + list(country.plane_group)
            ):
                names.add(group.name)
    # Spot checks: the FOB, the sea, the off-map rear and both factories.
    assert {
        "Mount Kent",
        "HMS Hermes",
        "HMS Invincible",
        "ARA Veinticinco de Mayo",
        "C82-UK-Falkland-Sound",
        "Ascension Island",
        "C82-SanCarlos-Factory",
        "C82-Stanley-Factory",
    } <= names
