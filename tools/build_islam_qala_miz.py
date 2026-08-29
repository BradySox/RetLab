"""Build resources/campaigns/islam_qala.miz from scratch.

*Afghanistan - Islam Qala* (October 1998): the US in the east at Bagram and Kabul
against an Iranian expeditionary force holding the west, with a spearhead already
at Chaghcharan. Design note:
``docs/dev/design/414th-islam-qala-campaign-notes.md``.

Built from an empty Afghanistan mission rather than forked from a shipped one.
Both Starfire Afghanistan campaigns were considered as bases and neither fits:
this laydown uses Bamyan, Chaghcharan and Qala i Naw, which no shipped campaign
on this map touches, and it drops Kandahar and Camp Bastion, which every one of
them uses. Deleting more than you keep is not a fork.

Three mechanisms this file depends on, each verified against the loader:

* **An airfield becomes a control point only when its coalition is set.** An
  untouched airport reads ``coalition = "NEUTRAL"`` with ``dynamic_spawn`` false,
  and ``Airport.is_neutral()`` returns False in that case, so
  ``MizCampaignLoader.control_points`` skips it. The fifteen fields not in
  ``AIRFIELDS`` below are therefore absent from the campaign, not neutral in it.
* **Do not set a field neutral to "leave it out".** The fork's
  ``control_point_from_airport`` reads ``if is_blue() ... else RED``, so a
  neutral-and-dynamic-spawn field enters the loop and comes out **red**.
* **Objective markers bind to the nearest control point.** No influence zones are
  authored here, so every static below is placed as an offset from the airfield
  it belongs to and binds there.

Deterministic: fixed offsets, no randomness. Vanilla units only, which is what
makes the pydcs round-trip safe -- see docs on mod-unit miz saves.

Usage: python tools/build_islam_qala_miz.py [--check]
       --check validates and prints the laydown without writing the miz.
"""

from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path
from typing import Iterable

from dcs.countries import CombinedJointTaskForcesBlue, CombinedJointTaskForcesRed
from dcs.mapping import LatLng, Point
from dcs.mission import Mission
from dcs.ships import Stennis
from dcs.statics import Fortification, Warehouse
from dcs.terrain.afghanistan import Afghanistan
from dcs.unittype import VehicleType
from dcs.vehicles import AirDefence, Armor, MissilesSS, Unarmed

REPO = Path(__file__).resolve().parent.parent
DST = REPO / "resources/campaigns/islam_qala.miz"
LANDMAP = REPO / "resources/theaters/afghanistan/landmap.p"

# The landmap pickle carries `game.theater` classes, so unpickling it needs the
# repo importable. Unlike the other build tools this one cannot run against a
# bare pydcs install.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

BLUE = CombinedJointTaskForcesBlue.name
RED = CombinedJointTaskForcesRed.name

# --------------------------------------------------------------- airfields ---
#: The eleven fields that become control points, by their pydcs airport name.
#: Everything else on the map stays out of the campaign entirely. Stand counts
#: are from the pydcs export and are the reason two of these carry no aircraft:
#: Chaghcharan has 3 and Bamyan 5, so both are positional, not basing.
AIRFIELDS: dict[str, str] = {
    # blue -- the eastern airhead
    "Bagram": BLUE,  # 187 stands
    "Kabul": BLUE,  # 192 stands
    "Bamyan": BLUE,  # 5 stands, rotary FARP
    "Ghazni Heliport": BLUE,  # 10 stands, southern shoulder
    # red -- the Iranian expeditionary force
    "Herat": RED,  # 36 stands, IRIAF fighter base
    "Shindand": RED,  # 52 stands, strike base
    "Shindand Heliport": RED,  # 42 stands
    "Qala i Naw": RED,  # 15 stands -- the reach prize, 55 nm from Herat
    "Chaghcharan": RED,  # 3 stands -- the spearhead
    "Farah": RED,  # 3 stands
    "Tarinkot": RED,  # 33 stands, southern shoulder
}

# ------------------------------------------------------------------ carrier ---
#: CVN-74 in the Arabian Sea. This exact position is carried over from
#: ``build_coin_enduring_resolve_miz.py``, where a Stennis placed here was proven
#: to float in the editor. Retribution's landmap has no sea polygons this far
#: south, so ``is_in_sea`` says no and DCS says yes; a carrier control point comes
#: straight from this sentinel, so DCS wins. Do not "fix" it against the landmap.
#:
#: 599 nm to Herat, 422 to Kandahar, 642 to Kabul. It is support-only -- see
#: ``CARRIER_IS_SUPPORT_ONLY`` in the campaign yaml's squadron block and the
#: design note's decision 1.
CARRIER = ("CVN-74 John C. Stennis", (-1046758.0, -99755.0))

# --------------------------------------------------------------------- FOBs ---
#: Yakawlang sits on the Bamyan-Chaghcharan road, the one intermediate objective
#: on the central axis. Real position; converted from lat/lon at build time so it
#: lands on the actual town rather than a guessed offset.
FOBS: tuple[tuple[str, str, tuple[float, float]], ...] = (
    ("FOB Yakawlang", RED, (34.7400, 66.9800)),
)

# ---------------------------------------------------------------------- AD ---
# Marker type decides the *category* of site; the actual system is drawn from the
# faction's presets at generation. Iran 1998 rosters no double-digit SAM, so a
# LORAD marker resolves to the S-200 and a MERAD marker to Hawk / S-75 / HQ-2 /
# SA-6. Blue's usa_1990 rosters Hawk and Patriot, both period-correct for 1998.
LORAD_MARKER = AirDefence.S_300PS_5P85C_ln
MERAD_MARKER = AirDefence.Hawk_ln
SHORAD_MARKER = AirDefence.rapier_fsa_launcher
AAA_MARKER = AirDefence.ZSU_23_4_Shilka
EWR_MARKER = AirDefence.x_1L13_EWR

#: Offsets in metres from the airfield centre. Spread so sites do not stack and
#: so a single strike cannot take two categories at once.
AD_OFFSETS: dict[str, tuple[float, float]] = {
    "lorad": (7500.0, 6200.0),
    "merad": (-6800.0, 5400.0),
    "shorad": (3200.0, -4100.0),
    "aaa": (-2600.0, -2900.0),
    "ewr": (11000.0, -8500.0),
}

#: Which categories each base gets. Chaghcharan is deliberately thin: a spearhead
#: at the end of an unpaved highland road does not have a radar SAM belt, and
#: making it soft is what invites the player up the central axis.
AIR_DEFENCE: dict[str, tuple[str, ...]] = {
    # red
    "Herat": ("lorad", "merad", "shorad", "aaa", "ewr"),
    "Shindand": ("lorad", "merad", "shorad", "aaa", "ewr"),
    "Qala i Naw": ("merad", "shorad", "aaa"),
    "Farah": ("merad", "shorad", "aaa"),
    "Tarinkot": ("merad", "shorad", "aaa"),
    "Shindand Heliport": ("aaa",),
    "Chaghcharan": ("shorad", "aaa"),
    # blue -- Patriot at Bagram is period-correct and answers Iran's Scuds.
    #
    # NO "aaa" on any blue base: usa_1990's air_defense_units are the FPS-117,
    # the Avenger and the M48 Chaparral, and it has no gun AAA at all. An AAA
    # marker on a blue field raises "USA 1990 has no access to SAM AAA" at
    # generation and produces nothing. SHORAD covers it -- which is also the
    # right answer historically, since US base defence in 1998 was Avenger and
    # Stinger rather than guns.
    "Bagram": ("lorad", "merad", "shorad", "ewr"),
    "Kabul": ("merad", "shorad", "ewr"),
    "Ghazni Heliport": ("shorad",),
    "Bamyan": ("shorad",),
}

# ------------------------------------------------------------- IADS C2 ------
# advanced_iads wires the network in range mode: comms nodes <= 15 nm, power
# sources <= 35 nm. These offsets keep every node well inside those radii of the
# base it serves, which is what makes §51 comms jamming, §52 decapitation and the
# bombed-power-station rule mean anything here.
C2_OFFSETS: dict[str, tuple[float, float]] = {
    "command_center": (-9500.0, -7200.0),
    "comms": (4600.0, 3900.0),
    "power": (-4200.0, 8100.0),
}

#: Command centres are the §52 decapitation targets. Two per side: enough that
#: losing one degrades planning without ending it.
COMMAND_CENTERS: tuple[str, ...] = ("Herat", "Shindand", "Bagram", "Kabul")
#: Every base with a radar SAM needs a comms node in range or its site is
#: orphaned from the network.
COMMS_NODES: tuple[str, ...] = (
    "Herat",
    "Shindand",
    "Qala i Naw",
    "Farah",
    "Tarinkot",
    "Chaghcharan",
    "Bagram",
    "Kabul",
)
POWER_SOURCES: tuple[str, ...] = ("Herat", "Shindand", "Farah", "Bagram", "Kabul")

# ------------------------------------------------------- economy / targets ---
#: (kind, base, count). Factories are income, ammo depots raise the front-line
#: density cap, motorpools are the §56 strikeable armour reserve, and strike
#: targets are the general-purpose Strike tasking pool.
ECONOMY: tuple[tuple[str, str, int], ...] = (
    # red rear -- Herat and Shindand are the Iranian logistics base
    ("factory", "Herat", 2),
    ("factory", "Shindand", 1),
    ("ammo", "Herat", 2),
    ("ammo", "Shindand", 2),
    ("ammo", "Farah", 1),
    ("ammo", "Qala i Naw", 1),
    ("motorpool", "Shindand", 1),
    ("motorpool", "Tarinkot", 1),
    ("strike", "Herat", 2),
    ("strike", "Shindand", 2),
    ("strike", "Farah", 1),
    # the spearhead is fed forward, not based -- one depot, nothing else
    ("ammo", "Chaghcharan", 1),
    # blue rear
    ("factory", "Bagram", 1),
    ("ammo", "Bagram", 2),
    ("ammo", "Kabul", 1),
    ("motorpool", "Kabul", 1),
    ("strike", "Kabul", 1),
)

ECONOMY_TYPES = {
    "factory": Fortification.Workshop_A,
    "ammo": Warehouse._Ammunition_depot,
    "motorpool": Fortification.Garage_A,
    "strike": Fortification.Tech_combine,
}

#: Ring the economy statics sit on, so several at one base do not overlap.
ECONOMY_RING: tuple[tuple[float, float], ...] = (
    (5200.0, 8800.0),
    (-8100.0, 3300.0),
    (6900.0, -7400.0),
    (-5600.0, -8900.0),
    (9600.0, 1800.0),
    (-1900.0, 9700.0),
)

#: Base-defence armour. The lever for BAI having anything to hit -- without these
#: the auto-planner runs short of ground targets and BAI packages thin out.
ARMOR_GROUPS: tuple[str, ...] = (
    "Herat",
    "Shindand",
    "Qala i Naw",
    "Farah",
    "Tarinkot",
    "Chaghcharan",
    "Bagram",
    "Kabul",
)
ARMOR_OFFSET = (-11200.0, -2400.0)

#: Iran's Shahab-1 (Scud-B) sites. These drive §49 mobile missile relocation --
#: fire first, then scoot -- and are the reason blue's Patriot at Bagram earns
#: its place. Placed at the two rear bases only; a Scud at the spearhead would be
#: within reach on turn one and the hunt would be over before it started.
MISSILE_SITES: tuple[str, ...] = ("Shindand", "Farah")
#: South-west, so that at Shindand it clears the heliport 1 nm to the NNE and
#: binds to the field itself. A north-east offset here put the Scud site on
#: Shindand Heliport instead.
MISSILE_OFFSET = (-13500.0, -4700.0)


#: Per-base shift applied to every marker at that base, on top of its own offset.
#:
#: Shindand and Shindand Heliport are 1 nm apart, and markers bind to the nearest
#: control point. Without this, Shindand's SAMs, EWR, command centre and Scud site
#: bound to the heliport instead -- harmless in a fight, but it splits one base's
#: air defence across two control points that can change hands separately. The
#: heliport sits NNE of the field, so Shindand's markers are pushed south-west.
BASE_BIAS: dict[str, tuple[float, float]] = {
    "Shindand": (-9000.0, -6500.0),
}


def _airport_position(mission: Mission, name: str) -> Point:
    airport = mission.terrain.airports.get(name)
    if airport is None:
        raise RuntimeError(
            f"{name!r} is not an airport on the Afghanistan terrain. "
            f"Known: {', '.join(sorted(mission.terrain.airports))}"
        )
    bias = BASE_BIAS.get(name, (0.0, 0.0))
    position = airport.position
    if bias == (0.0, 0.0):
        return position
    return Point(position.x + bias[0], position.y + bias[1], position._terrain)


def _offset(base: Point, delta: tuple[float, float], terrain: Afghanistan) -> Point:
    return Point(base.x + delta[0], base.y + delta[1], terrain)


def _load_inclusion_zones():  # type: ignore[no-untyped-def]
    """The landmap's land polygons.

    ``inclusion_zone_only`` is NOT a land test -- it subtracts the exclusion
    zones, and on other maps that has made good ground read as water. Use the
    inclusion zones directly, which is the check Anatolian Reach settled on.
    """
    with LANDMAP.open("rb") as f:
        landmap = pickle.load(f)
    return landmap.inclusion_zones


def _on_land(zones, point: Point) -> bool:  # type: ignore[no-untyped-def]
    from shapely.geometry import Point as ShapelyPoint

    return bool(zones.contains(ShapelyPoint(point.x, point.y)))


def build(check_only: bool = False) -> int:
    terrain = Afghanistan()
    mission = Mission(terrain)

    mission.coalition["blue"].add_country(CombinedJointTaskForcesBlue())
    mission.coalition["red"].add_country(CombinedJointTaskForcesRed())
    blue = mission.country(BLUE)
    red = mission.country(RED)
    assert blue is not None and red is not None

    def country(side: str):  # type: ignore[no-untyped-def]
        return blue if side == BLUE else red

    # --- airfields ------------------------------------------------------
    for name, side in AIRFIELDS.items():
        airport = mission.terrain.airports.get(name)
        if airport is None:
            raise RuntimeError(f"{name!r} is not an Afghanistan airport")
        if side == BLUE:
            airport.set_blue()
        else:
            airport.set_red()

    zones = _load_inclusion_zones()
    off_land: list[str] = []
    placed = {
        "airfield": len(AIRFIELDS),
        "carrier": 0,
        "fob": 0,
        "ad": 0,
        "c2": 0,
        "economy": 0,
        "armor": 0,
        "missile": 0,
    }

    def place_static(side: str, name: str, _type, position: Point) -> None:  # type: ignore[no-untyped-def]
        if not _on_land(zones, position):
            off_land.append(f"{name} ({position.x:.0f}, {position.y:.0f})")
        mission.static_group(
            country=country(side), name=name, _type=_type, position=position
        )

    def place_vehicle(side: str, name: str, _type, position: Point) -> None:  # type: ignore[no-untyped-def]
        if not _on_land(zones, position):
            off_land.append(f"{name} ({position.x:.0f}, {position.y:.0f})")
        mission.vehicle_group(
            country=country(side), name=name, _type=_type, position=position
        )

    # --- carrier --------------------------------------------------------
    carrier_name, (cx, cy) = CARRIER
    mission.ship_group(
        country=blue,
        name=carrier_name,
        _type=Stennis,
        position=Point(cx, cy, terrain),
    )
    placed["carrier"] = 1

    # --- FOBs -----------------------------------------------------------
    for fob_name, side, (lat, lon) in FOBS:
        position = Point.from_latlng(LatLng(lat, lon), terrain)
        place_vehicle(side, fob_name, Unarmed.SKP_11, position)
        placed["fob"] += 1

    # --- air defence ----------------------------------------------------
    markers = {
        "lorad": LORAD_MARKER,
        "merad": MERAD_MARKER,
        "shorad": SHORAD_MARKER,
        "aaa": AAA_MARKER,
        "ewr": EWR_MARKER,
    }
    for base, kinds in AIR_DEFENCE.items():
        side = AIRFIELDS[base]
        origin = _airport_position(mission, base)
        for kind in kinds:
            place_vehicle(
                side,
                f"{kind.upper()} {base}",
                markers[kind],
                _offset(origin, AD_OFFSETS[kind], terrain),
            )
            placed["ad"] += 1

    # --- IADS command and control ---------------------------------------
    for base in COMMAND_CENTERS:
        origin = _airport_position(mission, base)
        place_static(
            AIRFIELDS[base],
            f"CC {base}",
            Fortification._Command_Center,
            _offset(origin, C2_OFFSETS["command_center"], terrain),
        )
        placed["c2"] += 1
    for base in COMMS_NODES:
        origin = _airport_position(mission, base)
        place_static(
            AIRFIELDS[base],
            f"COMMS {base}",
            Fortification.Comms_tower_M,
            _offset(origin, C2_OFFSETS["comms"], terrain),
        )
        placed["c2"] += 1
    for base in POWER_SOURCES:
        origin = _airport_position(mission, base)
        place_static(
            AIRFIELDS[base],
            f"POWER {base}",
            Fortification.GeneratorF,
            _offset(origin, C2_OFFSETS["power"], terrain),
        )
        placed["c2"] += 1

    # --- economy and strike targets -------------------------------------
    ring_index: dict[str, int] = {}
    for kind, base, count in ECONOMY:
        origin = _airport_position(mission, base)
        for _ in range(count):
            slot = ring_index.get(base, 0)
            ring_index[base] = slot + 1
            place_static(
                AIRFIELDS[base],
                f"{kind.upper()} {base} {slot + 1}",
                ECONOMY_TYPES[kind],
                _offset(origin, ECONOMY_RING[slot % len(ECONOMY_RING)], terrain),
            )
            placed["economy"] += 1

    # --- base defence armour --------------------------------------------
    for base in ARMOR_GROUPS:
        origin = _airport_position(mission, base)
        place_vehicle(
            AIRFIELDS[base],
            f"ARMOR {base}",
            Armor.M_1_Abrams,
            _offset(origin, ARMOR_OFFSET, terrain),
        )
        placed["armor"] += 1

    # --- Scud sites ------------------------------------------------------
    for base in MISSILE_SITES:
        origin = _airport_position(mission, base)
        place_vehicle(
            AIRFIELDS[base],
            f"MISSILE {base}",
            MissilesSS.Scud_B,
            _offset(origin, MISSILE_OFFSET, terrain),
        )
        placed["missile"] += 1

    # --- report ----------------------------------------------------------
    blue_fields = [n for n, s in AIRFIELDS.items() if s == BLUE]
    red_fields = [n for n, s in AIRFIELDS.items() if s == RED]
    total_cps = len(AIRFIELDS) + 1 + len(FOBS)
    print(f"control points : {total_cps}")
    print(f"  blue         : {len(blue_fields)} airfields + 1 carrier")
    print(f"                 {', '.join(blue_fields)}")
    print(f"  red          : {len(red_fields)} airfields + {len(FOBS)} FOB")
    print(f"                 {', '.join(red_fields)}")
    print(f"                 {', '.join(f[0] for f in FOBS)}")
    print()
    for key, value in placed.items():
        print(f"  {key:<10}: {value}")
    print()

    if off_land:
        print(f"!! {len(off_land)} marker(s) landed off the landmap:")
        for entry in off_land:
            print(f"     {entry}")
        print("   Adjust the offset for that base; a marker in water is not")
        print("   guaranteed to bind or generate correctly.")
        return 1

    print("all markers on land")

    if check_only:
        print("--check: nothing written")
        return 0

    mission.save(str(DST))
    print(f"wrote {DST}")
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate and print the laydown without writing the miz",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    return build(check_only=args.check)


if __name__ == "__main__":
    sys.exit(main())
