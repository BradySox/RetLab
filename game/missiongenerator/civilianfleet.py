"""Which civil aircraft fly where, when, under whose name and paint.

Data, not logic: adding a map or re-crewing a region is an edit here and nothing
else. Design and the 2026-11-09 rebuild: ``docs/dev/design/retlab-civil-traffic-notes.md``.

Only real civil types in base DCS. The IL-76, An-30 and C-130 are gone: on radar they
read as military transports (Red Tide M1 lost an IL-76 to a Phoenix shot). The C-47 is
not here because it ships in the paid WWII Assets Pack. The An-26 flies only on the
ex-Soviet maps, where it really was civil traffic (DM call 2026-11-09).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from dcs.helicopters import Mi_8MT, UH_1H
from dcs.planes import An_26B, Christen_Eagle_II, Yak_40, Yak_52
from dcs.unittype import FlyingType


@dataclass(frozen=True)
class CivilType:
    """One civil airframe: how it cruises and the base-DCS paints that read civil."""

    aircraft: Type[FlyingType]
    #: First year it flew in civil service; a campaign before this never sees it.
    first_year: int
    altitude_m: int
    speed_ms: int
    #: True for low local traffic, which holds its height above the ground.
    agl: bool
    liveries: tuple[str, ...]

    @property
    def is_helicopter(self) -> bool:
        return bool(self.aircraft.helicopter)


YAK_40 = CivilType(
    Yak_40,
    1968,
    7_600,  # ~FL250
    150,
    False,
    ("Aeroflot", "Ukranian", "Georgian Airlines", "Olympic Airways"),
)
AN_26 = CivilType(An_26B, 1969, 6_100, 120, False, ("Aeroflot",))  # ~FL200
YAK_52 = CivilType(
    Yak_52, 1979, 900, 52, True, ("DOSAAF_RF", "DOSAAF_USSR", "Bare_Metall")
)
CHRISTEN_EAGLE = CivilType(
    Christen_Eagle_II, 1977, 900, 60, True, ("N104GF", "N14KH", "N22XS", "C-FTIJ")
)
MI_8 = CivilType(
    Mi_8MT,
    1967,
    300,
    50,
    True,
    ("Russia_Aeroflot", "Russia_UTair", "Russia_Gazprom", "Russia_Vertolety_Russia"),
)
UH_1 = CivilType(
    UH_1H, 1963, 300, 50, True, ("[Civilian] Standard", "[Civilian] Medical")
)


@dataclass(frozen=True)
class CivilRegion:
    """The civil air picture for one part of the world."""

    #: Fixed-wing types that fly the long, high airways.
    airliners: tuple[CivilType, ...]
    #: Light planes and helicopters that hop between nearby fields, low.
    local: tuple[CivilType, ...]
    #: Operator names for the callsign the F10 map shows ("AEROFLOT 412").
    operators: tuple[str, ...]

    def for_year(self, year: int) -> CivilRegion:
        """The same region with every type not yet in service removed."""
        return CivilRegion(
            airliners=tuple(t for t in self.airliners if t.first_year <= year),
            local=tuple(t for t in self.local if t.first_year <= year),
            operators=self.operators,
        )


#: A theater with no civil traffic at all (the 1944 maps).
CIVIL_TRAFFIC_NONE = CivilRegion(airliners=(), local=(), operators=())

_SOVIET_SPHERE = CivilRegion(
    airliners=(YAK_40, AN_26),
    local=(YAK_52, MI_8),
    operators=("AEROFLOT", "VOLGA AIR", "POLET", "URAL CARGO", "ARKTIKA"),
)

_CENTRAL_ASIA = CivilRegion(
    airliners=(YAK_40, AN_26),
    local=(MI_8,),
    operators=("ARIANA", "KAM AIR", "SILK ROUTE", "PAMIR CARGO"),
)

_LEVANT = CivilRegion(
    airliners=(YAK_40, AN_26),
    local=(MI_8, UH_1),
    operators=("CHAM WINGS", "LEVANT CARGO", "CEDAR AIR", "PALMYRA"),
)

_IRAQ = CivilRegion(
    airliners=(YAK_40,),
    local=(MI_8, UH_1),
    operators=("TIGRIS AIR", "BABYLON AIR", "BASRA CARGO", "EUPHRATES"),
)

_GULF = CivilRegion(
    airliners=(YAK_40,),
    local=(UH_1,),
    operators=("GULF FREIGHT", "KISH AIR", "DUBAI CARGO", "HORMUZ AIR"),
)

_WESTERN = CivilRegion(
    airliners=(YAK_40,),
    local=(CHRISTEN_EAGLE, UH_1),
    operators=("SKYWEST", "GRAND CANYON AIR", "PACIFIC FREIGHT", "DESERT AIR"),
)

_COLD_WAR_EUROPE = CivilRegion(
    airliners=(YAK_40,),
    local=(YAK_52, UH_1, MI_8),
    operators=("INTERFLUG", "LOT", "BALKAN AIR", "MALEV"),
)

#: Keyed by ``dcs.terrain.Terrain.name``, never the campaign yaml's display name. An
#: unknown map falls back to the Soviet sphere: those airframes are on every install.
REGIONS: dict[str, CivilRegion] = {
    "Caucasus": _SOVIET_SPHERE,
    "Kola": _SOVIET_SPHERE,
    "Afghanistan": _CENTRAL_ASIA,
    "Syria": _LEVANT,
    "Iraq": _IRAQ,
    "SinaiMap": _GULF,
    "PersianGulf": _GULF,
    "Nevada": _WESTERN,
    "MarianaIslands": _WESTERN,
    "Falklands": _WESTERN,
    "GermanyCW": _COLD_WAR_EUROPE,
    "Normandy": CIVIL_TRAFFIC_NONE,
    "TheChannel": CIVIL_TRAFFIC_NONE,
    "MarianaIslandsWWII": CIVIL_TRAFFIC_NONE,
}

DEFAULT_REGION = _SOVIET_SPHERE

#: Every type the regions use, for the guards in the tests.
ALL_TYPES: tuple[CivilType, ...] = (YAK_40, AN_26, YAK_52, CHRISTEN_EAGLE, MI_8, UH_1)


def region_for(terrain_name: str) -> CivilRegion:
    """The civil air picture for a terrain, by ``Terrain.name``."""
    return REGIONS.get(terrain_name, DEFAULT_REGION)
