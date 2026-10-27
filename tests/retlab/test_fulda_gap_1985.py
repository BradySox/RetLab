"""Germany - Fulda Gap 1985 laydown guards.

The Central Front in September 1985: NATO holds the Rhineland and Hesse, the
Group of Soviet Forces in Germany and the East German air force hold Thuringia,
Saxony-Anhalt and the fields south of Berlin. Three border crossings.

What these pin is what fails silently:

* a red control point without the invert flag stays red in an inverted game;
* a road drawn to the wrong control point moves a front line;
* both factions are stock DCS, so the campaign needs no mod box ticked;
* DCS stands are nested, so a base's slot count is not the constraint.

Design note: docs/dev/design/retlab-fulda-gap-1985-campaign-notes.md
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
from game.theater.controlpoint import Airfield, Fob
from game.theater.start_generator import ModSettings

YAML = Path("resources/campaigns/fulda_gap_1985.yaml")
MIZ = Path("resources/campaigns/fulda_gap_1985.miz")

NATO = "NATO Central Front 1985"
PACT = "Warsaw Pact Central Front 1985"
OBERMEHLER = "Obermehler Schlotheim"
MEININGEN = "Meiningen"
#: Cut from 26 to 13 by the DM, 2026-10-24: front and key fields only.
BLUE = {
    "Spangdahlem",
    "Bitburg",
    "Ramstein",
    "Frankfurt",
    "Fulda",
    "Fritzlar",
    "Schweinfurt",
}
RED = {"Haina", OBERMEHLER, MEININGEN, "Bindersleben", "Allstedt", "Merseburg"}
ROADS = {
    frozenset(pair)
    for pair in (
        ("Bitburg", "Spangdahlem"),
        ("Spangdahlem", "Frankfurt"),
        ("Ramstein", "Frankfurt"),
        ("Frankfurt", "Fulda"),
        ("Frankfurt", "Fritzlar"),
        ("Frankfurt", "Schweinfurt"),
        ("Fulda", "Fritzlar"),
        ("Fulda", "Haina"),
        ("Schweinfurt", MEININGEN),
        (MEININGEN, "Bindersleben"),
        (OBERMEHLER, "Haina"),
        ("Haina", "Bindersleben"),
        ("Bindersleben", "Allstedt"),
        ("Allstedt", "Merseburg"),
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
    persistency.setup(str(tmp_path_factory.mktemp("fulda-gap-1985")), False, 0)
    campaign = Campaign.from_file(YAML)
    return campaign, campaign.load_theater(campaign.advanced_iads)


def test_the_date(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    start = campaign.recommended_start_date
    assert start is not None
    assert (start.year, start.month) == (1985, 9)


def test_both_factions_are_stock(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), False, 0)
    for name in (NATO, PACT):
        faction = copy.deepcopy(FACTIONS[name])
        # ``all_aircrafts`` is cached; the stripped set is ``aircraft``.
        before = {a.display_name for a in faction.aircraft}
        faction.apply_mod_settings(ModSettings.all_off())
        assert {a.display_name for a in faction.aircraft} == before, name


def test_who_holds_what(loaded: tuple[Campaign, ConflictTheater]) -> None:
    _, theater = loaded
    blue = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_blue}
    red = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_red}
    assert blue == BLUE
    assert red == RED
    # Every field outside the sector holds nothing, and nothing is off the map.
    assert len(theater.controlpoints) == len(BLUE) + len(RED)
    fobs = {cp.name for cp in theater.controlpoints if isinstance(cp, Fob)}
    assert fobs == {MEININGEN}
    assert all(
        isinstance(cp, Airfield) for cp in theater.controlpoints if cp.name != MEININGEN
    )


def test_every_red_point_inverts_and_no_blue_one_does(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    for cp in theater.controlpoints:
        assert cp.captured_invert is cp.starting_coalition.is_red, cp.name


def test_the_three_crossings(loaded: tuple[Campaign, ConflictTheater]) -> None:
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
    # The Fulda Gap and the Meiningen road: a two-front war (the DM's call).
    assert opposed == {
        frozenset(("Fulda", "Haina")),
        frozenset(("Schweinfurt", MEININGEN)),
    }


def test_the_victory_rules(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    victory = campaign.data["victory"]
    assert victory["win_when"][0]["capture_cps"] == ["Bindersleben", "Merseburg"]
    assert victory["lose_when"][0]["lose_cps"] == ["Frankfurt"]


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


def test_the_23rd_flies_from_spangdahlem(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """The squadron the campaign was built for, with its 52nd TFW sisters."""
    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    spangdahlem = theater.control_point_named("Spangdahlem")
    names = {s.aircraft[0] for s in config.by_location[spangdahlem]}
    assert names == {
        "23rd Tactical Fighter Squadron",
        "480th Tactical Fighter Squadron",
    }


def test_the_soviet_iads_net(loaded: tuple[Campaign, ConflictTheater]) -> None:
    """Skynet in range mode: the 8th Guards Army HQ, comms and power on real places."""
    campaign, _ = loaded
    assert campaign.advanced_iads
    mission = _miz()
    statics = [
        group.units[0].type
        for country in mission.coalition["red"].countries.values()
        for group in country.static_group
        if group.name.startswith("CF85-IADS-")
    ]
    assert statics.count(".Command Center") == 1
    assert statics.count("Comms tower M") == 12
    assert statics.count("GeneratorF") == 4
    # NATO's Patriot is the one long-range marker. Red has no SA-5: its rings
    # covered all of West Germany (the DM's call, 2026-10-24).
    longs = sorted(
        group.name
        for country in mission.coalition["red"].countries.values()
        for group in country.vehicle_group
        if group.units[0].type == "S-300PS 5P85C ln"
    )
    assert longs == ["CF85-Ramstein-Patriot"]
    for country in mission.coalition["blue"].countries.values():
        assert not any(g.name.startswith("CF85-IADS-") for g in country.static_group)


def test_red_tides_scenery_targets_come_with_it(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    groups = [g for cp in theater.controlpoints for g in cp.preset_locations.scenery]
    assert len(groups) == 26
    zones = {zone.name for group in groups for zone in group.zones}
    assert {"Haina IADS CmdCenter Bldg", "Staudinger Power Station"} <= zones


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


def test_carstens_sites_are_drawn_unit_by_unit(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """22 FIXED sites: Hawks for NATO, SA-2/3/5 and S-60 for red."""
    _, theater = loaded
    sites = {
        site.original_name: cp
        for cp in theater.controlpoints
        for site in cp.preset_locations.exact_air_defenses
    }
    assert len(sites) == 22
    # The DM placed Kaltennordheim's launchers himself; it and Eckolstadt were
    # SA-5s and are SA-2s in the same revetments.
    assert {"FIXED SA-2 Kaltennordheim", "FIXED SA-2 Eckolstadt"} <= set(sites)
    assert not any("SA-5" in name for name in sites)
    assert "SA-5/S-200" not in {pg.name for pg in FACTIONS[PACT].preset_groups}
    hawks = {name for name in sites if name.startswith("FIXED Hawk ")}
    assert len(hawks) == 10
    for name, cp in sites.items():
        assert cp.starting_coalition.is_blue is (name in hawks), (name, cp.name)
    # Every non-truck unit is one the owner can field, or a stock site replaces it.
    for kind in ("S-60 57mm", "AAA Fire Can SON-9"):
        assert kind in {u.display_name for u in FACTIONS[PACT].accessible_units}, kind
    # No MiG-29s: the DM's call, 2026-10-24.
    assert not any("MiG-29" in a.display_name for a in FACTIONS[PACT].all_aircrafts)


def test_the_1985_neighbours_take_sides(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    # Test 65: with no field on the map, NATO's neighbours read neutral and
    # stood up SA-2s against blue.
    _, theater = loaded
    pinned = {z.country: z.posture_override for z in theater.neutral_border_zones}
    for country in ("Belgium", "The Netherlands", "Denmark", "France", "Luxembourg"):
        assert pinned[country] == "blue", country
    for country in ("Czech Republic", "Slovakia", "Poland", "Hungary"):
        assert pinned[country] == "red", country
    for country in ("Austria", "Switzerland", "Sweden", "GDR", "Germany"):
        assert pinned[country] is None, country
