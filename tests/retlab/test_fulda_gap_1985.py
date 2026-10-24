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
BLUE = {
    "Spangdahlem",
    "Bitburg",
    "Hahn",
    "Ramstein",
    "Sembach",
    "Pferdsfeld",
    "Frankfurt",
    "Norvenich",
    "Gutersloh",
    "Fulda",
    "Fritzlar",
    "Giebelstadt",
    "Schweinfurt",
}
RED = {
    "Haina",
    OBERMEHLER,
    MEININGEN,
    "Bindersleben",
    "Allstedt",
    "Merseburg",
    "Kothen",
    "Zerbst",
    "Brandis",
    "Altes Lager",
    "Holzdorf",
    "Mahlwinkel",
    "Sperenberg",
}
ROADS = {
    frozenset(pair)
    for pair in (
        ("Bitburg", "Spangdahlem"),
        ("Norvenich", "Bitburg"),
        ("Spangdahlem", "Hahn"),
        ("Pferdsfeld", "Hahn"),
        ("Hahn", "Frankfurt"),
        ("Ramstein", "Sembach"),
        ("Sembach", "Frankfurt"),
        ("Frankfurt", "Fulda"),
        ("Frankfurt", "Fritzlar"),
        ("Frankfurt", "Giebelstadt"),
        ("Giebelstadt", "Schweinfurt"),
        ("Fulda", "Fritzlar"),
        ("Fulda", "Haina"),
        ("Fritzlar", OBERMEHLER),
        ("Schweinfurt", MEININGEN),
        (MEININGEN, "Bindersleben"),
        (OBERMEHLER, "Haina"),
        ("Haina", "Bindersleben"),
        ("Bindersleben", "Allstedt"),
        ("Allstedt", "Merseburg"),
        ("Merseburg", "Brandis"),
        ("Merseburg", "Kothen"),
        ("Kothen", "Zerbst"),
        ("Zerbst", "Altes Lager"),
        ("Altes Lager", "Sperenberg"),
        ("Brandis", "Holzdorf"),
        ("Mahlwinkel", "Kothen"),
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
    # The RAF Tornados' field is a rear base with no road to the war.
    assert not theater.control_point_named("Gutersloh").connected_points


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
    # The Fulda Gap, the Werra valley and the Meiningen road.
    assert opposed == {
        frozenset(("Fulda", "Haina")),
        frozenset(("Fritzlar", OBERMEHLER)),
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
        "81st Tactical Fighter Squadron (1985)",
    }


def test_the_soviet_iads_net(loaded: tuple[Campaign, ConflictTheater]) -> None:
    """Skynet in range mode: three HQs, comms towers and power on real places."""
    campaign, _ = loaded
    assert campaign.advanced_iads
    mission = _miz()
    statics = [
        group.units[0].type
        for country in mission.coalition["red"].countries.values()
        for group in country.static_group
        if group.name.startswith("CF85-IADS-")
    ]
    assert statics.count(".Command Center") == 3
    assert statics.count("Comms tower M") == 15
    assert statics.count("GeneratorF") == 6
    # Three SA-5s at Carsten's sites; NATO's one long-range marker is Ramstein's.
    longs = sorted(
        group.name
        for country in mission.coalition["red"].countries.values()
        for group in country.vehicle_group
        if group.units[0].type == "S-300PS 5P85C ln"
    )
    assert longs == [
        "CF85-Ramstein-Patriot",
        "CF85-SA5-Eckolstadt",
        "CF85-SA5-Kaltennordheim",
        "CF85-SA5-Magdeburg",
    ]
    for country in mission.coalition["blue"].countries.values():
        assert not any(g.name.startswith("CF85-IADS-") for g in country.static_group)


def test_red_tides_scenery_targets_come_with_it(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    groups = [g for cp in theater.controlpoints for g in cp.preset_locations.scenery]
    assert len(groups) == 37
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


def test_the_fixed_sams_fill_as_their_real_types(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """Carsten's sites: each binds a red point and fills as the site's own type."""
    campaign, theater = loaded
    pinned = campaign.data["ground_forces"]
    sites = [n for n in pinned if n.startswith(("CF85-SA2-", "CF85-SA3-", "CF85-SA5-"))]
    assert len(sites) == 14
    for name in sites:
        kind = name.split("-")[1]
        assert pinned[name].startswith(f"SA-{kind[2]}/"), name
    # No MiG-29s: the DM's call, 2026-10-24.
    assert not any("MiG-29" in a.display_name for a in FACTIONS[PACT].all_aircrafts)
