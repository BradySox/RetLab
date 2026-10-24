"""Build ``resources/campaigns/fulda_gap_1985.miz``: Germany - Fulda Gap 1985.

The Central Front in September 1985. NATO's 4th Allied Tactical Air Force holds the
Rhineland bases and the Hessian border; the Group of Soviet Forces in Germany, its
16th Air Army and the East German air force hold Thuringia, Saxony-Anhalt and the
fields south of Berlin. Three crossings: the Fulda Gap to Eisenach, the Werra valley
to Muhlhausen, and the Meiningen road to Erfurt.

Design note: docs/dev/design/retlab-fulda-gap-1985-campaign-notes.md

What it writes, starting from ``red_tide.miz`` for the map and its scenery targets:

1.  **Ownership.** Thirteen NATO fields, twelve Warsaw Pact fields and the Meiningen
    FOB; every other field is neutral with dynamic spawn off.
2.  **Invert Sides.** Every red control point carries the invert flag.
3.  **Scenery.** Red Tide's scenery target sets inside the central sector; its
    markers, influence zones and every group are dropped.
4.  **The land.** Base defenses, garrisons, depots, two Scud batteries, and the
    Soviet IADS nodes (HQs, comms towers, power) on real places.
5.  **The roads.** One M-113 route group per road, traced from real town lat/lon,
    On Road between first and last waypoints that are Off Road.

Run from the repo root::

    python tools/build_fulda_gap_1985_miz.py

Once the DM edits the laydown in the Mission Editor, his save is the source and this
tool is deleted, as Red Bear 1985's was.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable, Union

from dcs.countries import CombinedJointTaskForcesBlue
from dcs.mapping import LatLng, Point
from dcs.mission import Mission
from dcs.point import PointAction
from dcs.statics import Fortification, Warehouse
from dcs.terrain.terrain import Airport
from dcs.triggers import TriggerZone
from dcs.vehicles import AirDefence, Armor, MissilesSS, Unarmed

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from game.campaignloader.mizcampaignloader import MizCampaignLoader  # noqa: E402

SOURCE = _REPO_ROOT / "resources/campaigns/red_tide.miz"
SOURCE_YAML = _REPO_ROOT / "resources/campaigns/red_tide.yaml"
DEST = _REPO_ROOT / "resources/campaigns/fulda_gap_1985.miz"

BLUE_AIRFIELDS = (
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
)
RED_AIRFIELDS = (
    "Haina",
    "Obermehler Schlotheim",
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
)
OBERMEHLER = "Obermehler Schlotheim"
#: The Soviet garrison at Meiningen holds the Meiningen road. Without it the
#: Meiningen SA-3 binds to Fulda, the nearest control point.
MEININGEN = "Meiningen"
FOBS = ((MEININGEN, 50.585, 10.420),)

#: The central sector: Red Tide scenery sets outside it are dropped.
SECTOR_LAT = (49.2, 52.45)
SECTOR_LON = (6.3, 13.5)

# --- Marker vocabulary (must match MizCampaignLoader's *_UNIT_TYPE(S)) ---------
EWR = AirDefence.x_1L13_EWR
LONG_SAM = AirDefence.S_300PS_5P85C_ln
MEDIUM_SAM = AirDefence.S_75M_Volhov
SHORAD = AirDefence.Strela_1_9P31
AAA = AirDefence.ZSU_23_4_Shilka
ARMOR = Armor.M_1_Abrams

RED_BLOCK = "red"
BLUE_BLOCK = "blue"

Anchor = Union[str, tuple[float, float]]

# (name, anchor, marker type, country block, placement). An anchor is an airfield
# name or a (lat, lon). Placement: "ring" 3-15 km out, "near" within 6 km first,
# "axis" off the runway ends, "at" on the spot or as close as clear land allows.
# SAM and EWR markers go in the red block, the loader's side-agnostic default.
ADDED_MARKERS: tuple[tuple[str, Anchor, Any, str, str], ...] = (
    # NATO's Hawk belt and CRC at the sites in Carsten's Cold War Germany Framework.
    ("CF85-Hawk-Frielendorf", (50.9263, 9.4994), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-Hawk-Kassel", (51.3923, 9.5379), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-Hawk-Bruchkobel", (50.1729, 8.9652), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-Hawk-Giessen", (50.5756, 8.7376), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-Hawk-Fulda", (50.5531, 9.5422), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-Hawk-Rockenhausen", (49.6282, 7.7570), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-Hawk-Baumholder", (49.6294, 7.2928), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-Hawk-Schmallenberg", (51.2000, 8.1101), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-Hawk-Steinheim", (51.8949, 9.2317), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-Hawk-Bad-Driburg", (51.7294, 8.9876), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-CRC-Erndtebruck-EWR", (50.9910, 8.2300), EWR, RED_BLOCK, "at"),
    ("CF85-Wasserkuppe-EWR", (50.498, 9.938), EWR, RED_BLOCK, "at"),
    ("CF85-Ramstein-Patriot", "Ramstein", LONG_SAM, RED_BLOCK, "ring"),
    # NATO airfield defense: Roland, Rapier, Gepard and Vulcan.
    ("CF85-Spangdahlem-SHORAD", "Spangdahlem", SHORAD, RED_BLOCK, "near"),
    ("CF85-Spangdahlem-AAA-1", "Spangdahlem", AAA, RED_BLOCK, "near"),
    ("CF85-Spangdahlem-AAA-2", "Spangdahlem", AAA, RED_BLOCK, "near"),
    ("CF85-Bitburg-SHORAD", "Bitburg", SHORAD, RED_BLOCK, "near"),
    ("CF85-Bitburg-AAA", "Bitburg", AAA, RED_BLOCK, "near"),
    ("CF85-Hahn-SHORAD", "Hahn", SHORAD, RED_BLOCK, "near"),
    ("CF85-Hahn-AAA", "Hahn", AAA, RED_BLOCK, "near"),
    ("CF85-Ramstein-AAA-1", "Ramstein", AAA, RED_BLOCK, "near"),
    ("CF85-Ramstein-AAA-2", "Ramstein", AAA, RED_BLOCK, "near"),
    ("CF85-Sembach-SHORAD", "Sembach", SHORAD, RED_BLOCK, "near"),
    ("CF85-Sembach-AAA", "Sembach", AAA, RED_BLOCK, "near"),
    ("CF85-Pferdsfeld-SHORAD", "Pferdsfeld", SHORAD, RED_BLOCK, "near"),
    ("CF85-Pferdsfeld-AAA", "Pferdsfeld", AAA, RED_BLOCK, "near"),
    ("CF85-Frankfurt-SHORAD", "Frankfurt", SHORAD, RED_BLOCK, "near"),
    ("CF85-Frankfurt-AAA-1", "Frankfurt", AAA, RED_BLOCK, "near"),
    ("CF85-Frankfurt-AAA-2", "Frankfurt", AAA, RED_BLOCK, "near"),
    ("CF85-Norvenich-SHORAD", "Norvenich", SHORAD, RED_BLOCK, "near"),
    ("CF85-Norvenich-AAA", "Norvenich", AAA, RED_BLOCK, "near"),
    ("CF85-Gutersloh-SHORAD", "Gutersloh", SHORAD, RED_BLOCK, "near"),
    ("CF85-Gutersloh-AAA", "Gutersloh", AAA, RED_BLOCK, "near"),
    ("CF85-Fulda-SHORAD", "Fulda", SHORAD, RED_BLOCK, "near"),
    ("CF85-Fulda-Blackhorse-1", "Fulda", ARMOR, BLUE_BLOCK, "near"),
    ("CF85-Fulda-Blackhorse-2", "Fulda", ARMOR, BLUE_BLOCK, "near"),
    ("CF85-Fritzlar-SHORAD", "Fritzlar", SHORAD, RED_BLOCK, "near"),
    ("CF85-Fritzlar-AAA", "Fritzlar", AAA, RED_BLOCK, "near"),
    ("CF85-Fritzlar-Garrison-1", "Fritzlar", ARMOR, BLUE_BLOCK, "near"),
    ("CF85-Fritzlar-Garrison-2", "Fritzlar", ARMOR, BLUE_BLOCK, "near"),
    ("CF85-Giebelstadt-SHORAD", "Giebelstadt", SHORAD, RED_BLOCK, "near"),
    ("CF85-Giebelstadt-AAA", "Giebelstadt", AAA, RED_BLOCK, "near"),
    ("CF85-Schweinfurt-SHORAD", "Schweinfurt", SHORAD, RED_BLOCK, "near"),
    ("CF85-Schweinfurt-Garrison-1", "Schweinfurt", ARMOR, BLUE_BLOCK, "near"),
    ("CF85-Schweinfurt-Garrison-2", "Schweinfurt", ARMOR, BLUE_BLOCK, "near"),
    # The 8th Guards Army on the border: SA-6s standing in for its SA-4 brigade,
    # guns and tank divisions.
    ("CF85-Haina-SA6", "Haina", MEDIUM_SAM, RED_BLOCK, "ring"),
    ("CF85-Haina-SHORAD", "Haina", SHORAD, RED_BLOCK, "near"),
    ("CF85-Haina-AAA-1", "Haina", AAA, RED_BLOCK, "near"),
    ("CF85-Haina-AAA-2", "Haina", AAA, RED_BLOCK, "near"),
    ("CF85-Haina-EWR", "Haina", EWR, RED_BLOCK, "ring"),
    ("CF85-Haina-Armor-1", "Haina", ARMOR, RED_BLOCK, "near"),
    ("CF85-Haina-Armor-2", "Haina", ARMOR, RED_BLOCK, "near"),
    ("CF85-Haina-Armor-3", "Haina", ARMOR, RED_BLOCK, "near"),
    ("CF85-Obermehler-SA6", OBERMEHLER, MEDIUM_SAM, RED_BLOCK, "ring"),
    ("CF85-Obermehler-SHORAD", OBERMEHLER, SHORAD, RED_BLOCK, "near"),
    ("CF85-Obermehler-AAA", OBERMEHLER, AAA, RED_BLOCK, "near"),
    ("CF85-Obermehler-Armor-1", OBERMEHLER, ARMOR, RED_BLOCK, "near"),
    ("CF85-Obermehler-Armor-2", OBERMEHLER, ARMOR, RED_BLOCK, "near"),
    ("CF85-Meiningen-SHORAD", MEININGEN, SHORAD, RED_BLOCK, "near"),
    ("CF85-Meiningen-AAA", MEININGEN, AAA, RED_BLOCK, "near"),
    ("CF85-Meiningen-Armor-1", MEININGEN, ARMOR, RED_BLOCK, "near"),
    ("CF85-Meiningen-Armor-2", MEININGEN, ARMOR, RED_BLOCK, "near"),
    ("CF85-Erfurt-SA6", "Bindersleben", MEDIUM_SAM, RED_BLOCK, "ring"),
    ("CF85-Erfurt-SHORAD", "Bindersleben", SHORAD, RED_BLOCK, "near"),
    ("CF85-Erfurt-AAA", "Bindersleben", AAA, RED_BLOCK, "near"),
    ("CF85-Erfurt-EWR", "Bindersleben", EWR, RED_BLOCK, "ring"),
    ("CF85-Erfurt-Armor-1", "Bindersleben", ARMOR, RED_BLOCK, "near"),
    ("CF85-Erfurt-Armor-2", "Bindersleben", ARMOR, RED_BLOCK, "near"),
    # Roadside SHORAD on the crossings and the rear roads.
    ("CF85-Road-SHORAD-Eisenach", (50.975, 10.320), SHORAD, RED_BLOCK, "near"),
    ("CF85-Road-SHORAD-Muhlhausen", (51.208, 10.453), SHORAD, RED_BLOCK, "near"),
    ("CF85-Road-SHORAD-Gotha", (50.948, 10.701), SHORAD, RED_BLOCK, "near"),
    ("CF85-Road-SHORAD-Halle", (51.483, 11.970), SHORAD, RED_BLOCK, "near"),
    ("CF85-Road-SHORAD-Dessau", (51.835, 12.246), SHORAD, RED_BLOCK, "near"),
    # The GDR and Soviet SA-2, SA-3 and SA-5 sites and S-60 batteries, at the
    # sites in Carsten's Cold War Germany Framework.
    ("CF85-SA3-Meiningen", (50.5872, 10.2677), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-SA2-Gotha", (50.9609, 10.6394), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-SA2-Allstedt", (51.4180, 11.3957), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-SA2-Quedlinburg", (51.7529, 11.1436), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-SA2-Merseburg", (51.3804, 11.8331), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-SA2-Bad-Durrenberg", (51.3324, 12.1538), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-SA2-Leipzig", (51.3371, 12.5742), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-SA2-Kothen", (51.7087, 11.8665), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-SA2-Dessau", (51.7487, 12.2062), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-SA2-Mahlwinkel", (52.3648, 11.7008), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-SA3-Sperenberg", (52.1958, 13.2586), MEDIUM_SAM, RED_BLOCK, "at"),
    ("CF85-SA5-Kaltennordheim", (50.7240, 10.1536), LONG_SAM, RED_BLOCK, "at"),
    ("CF85-SA5-Eckolstadt", (51.0501, 11.6233), LONG_SAM, RED_BLOCK, "at"),
    ("CF85-SA5-Magdeburg", (52.1605, 12.0315), LONG_SAM, RED_BLOCK, "at"),
    ("CF85-S60-Leipzig", (51.4112, 12.2047), AAA, RED_BLOCK, "at"),
    ("CF85-S60-Burg", (52.2157, 11.7730), AAA, RED_BLOCK, "at"),
    ("CF85-S60-Potsdam", (52.3615, 13.0369), AAA, RED_BLOCK, "at"),
    # The 16th Air Army's fields.
    ("CF85-Allstedt-SHORAD", "Allstedt", SHORAD, RED_BLOCK, "near"),
    ("CF85-Allstedt-AAA", "Allstedt", AAA, RED_BLOCK, "near"),
    ("CF85-Merseburg-SHORAD", "Merseburg", SHORAD, RED_BLOCK, "near"),
    ("CF85-Merseburg-AAA", "Merseburg", AAA, RED_BLOCK, "near"),
    ("CF85-Merseburg-EWR", "Merseburg", EWR, RED_BLOCK, "ring"),
    ("CF85-Kothen-AAA", "Kothen", AAA, RED_BLOCK, "near"),
    ("CF85-Zerbst-SHORAD", "Zerbst", SHORAD, RED_BLOCK, "near"),
    ("CF85-Zerbst-AAA", "Zerbst", AAA, RED_BLOCK, "near"),
    ("CF85-Brandis-SHORAD", "Brandis", SHORAD, RED_BLOCK, "near"),
    ("CF85-Brandis-AAA", "Brandis", AAA, RED_BLOCK, "near"),
    ("CF85-Brandis-EWR", "Brandis", EWR, RED_BLOCK, "ring"),
    ("CF85-AltesLager-SHORAD", "Altes Lager", SHORAD, RED_BLOCK, "near"),
    ("CF85-AltesLager-AAA", "Altes Lager", AAA, RED_BLOCK, "near"),
    ("CF85-AltesLager-EWR", "Altes Lager", EWR, RED_BLOCK, "ring"),
    ("CF85-Holzdorf-SHORAD", "Holzdorf", SHORAD, RED_BLOCK, "near"),
    ("CF85-Holzdorf-AAA", "Holzdorf", AAA, RED_BLOCK, "near"),
    ("CF85-Mahlwinkel-AAA", "Mahlwinkel", AAA, RED_BLOCK, "near"),
    ("CF85-Mahlwinkel-EWR", "Mahlwinkel", EWR, RED_BLOCK, "ring"),
    ("CF85-Sperenberg-SHORAD", "Sperenberg", SHORAD, RED_BLOCK, "near"),
    ("CF85-Sperenberg-AAA", "Sperenberg", AAA, RED_BLOCK, "near"),
    ("CF85-Sperenberg-EWR", "Sperenberg", EWR, RED_BLOCK, "ring"),
)

#: The GSFG Scud brigades: one behind the 8th Guards Army at Weimar, one at Juterbog.
SCUD_SITES = (
    ("CF85-Weimar-Scud", (50.990, 11.300)),
    ("CF85-Juterbog-Scud", (51.960, 13.120)),
)

#: (name, anchor, static type, block). Ownership follows the nearest control point.
ADDED_STATICS: tuple[tuple[str, Anchor, Any, str, str], ...] = (
    (
        "CF85-Spangdahlem-Ammo",
        "Spangdahlem",
        Warehouse._Ammunition_depot,
        BLUE_BLOCK,
        "near",
    ),
    ("CF85-Ramstein-Ammo", "Ramstein", Warehouse._Ammunition_depot, BLUE_BLOCK, "near"),
    (
        "CF85-Frankfurt-Ammo",
        "Frankfurt",
        Warehouse._Ammunition_depot,
        BLUE_BLOCK,
        "near",
    ),
    (
        "CF85-Frankfurt-Motorpool",
        "Frankfurt",
        Fortification.Garage_A,
        BLUE_BLOCK,
        "near",
    ),
    ("CF85-Fulda-Ammo", "Fulda", Warehouse._Ammunition_depot, BLUE_BLOCK, "near"),
    ("CF85-Fritzlar-Motorpool", "Fritzlar", Fortification.Garage_A, BLUE_BLOCK, "near"),
    ("CF85-Haina-Ammo", "Haina", Warehouse._Ammunition_depot, RED_BLOCK, "near"),
    ("CF85-Haina-Motorpool", "Haina", Fortification.Garage_A, RED_BLOCK, "near"),
    (
        "CF85-Erfurt-Ammo",
        "Bindersleben",
        Warehouse._Ammunition_depot,
        RED_BLOCK,
        "near",
    ),
    ("CF85-Allstedt-Ammo", "Allstedt", Warehouse._Ammunition_depot, RED_BLOCK, "near"),
    ("CF85-Buna-Works", (51.390, 11.970), Fortification.Workshop_A, RED_BLOCK, "at"),
    ("CF85-Leuna-Works", (51.315, 12.015), Fortification.Workshop_A, RED_BLOCK, "at"),
    ("CF85-Kothen-Motorpool", "Kothen", Fortification.Garage_A, RED_BLOCK, "near"),
    ("CF85-Brandis-Ammo", "Brandis", Warehouse._Ammunition_depot, RED_BLOCK, "near"),
    (
        "CF85-AltesLager-Ammo",
        "Altes Lager",
        Warehouse._Ammunition_depot,
        RED_BLOCK,
        "near",
    ),
)

#: The Soviet IADS (Skynet's advanced mode, wired by range): HQs, comms and power.
COMMAND_CENTER = Fortification._Command_Center
COMMS = Fortification.Comms_tower_M
POWER = Fortification.GeneratorF
IADS_NODES: tuple[tuple[str, Any, float, float], ...] = (
    ("CF85-IADS-HQ-Wunsdorf", COMMAND_CENTER, 52.170, 13.470),
    ("CF85-IADS-HQ-Weimar-8GA", COMMAND_CENTER, 50.975, 11.345),
    ("CF85-IADS-HQ-Magdeburg-3SA", COMMAND_CENTER, 52.125, 11.625),
    ("CF85-IADS-Comms-Inselsberg", COMMS, 50.852, 10.468),
    ("CF85-IADS-Comms-Brocken", COMMS, 51.799, 10.616),
    ("CF85-IADS-Comms-Eisenach", COMMS, 50.985, 10.335),
    ("CF85-IADS-Comms-Muhlhausen", COMMS, 51.215, 10.470),
    ("CF85-IADS-Comms-Meiningen", COMMS, 50.575, 10.430),
    ("CF85-IADS-Comms-Erfurt", COMMS, 50.965, 11.040),
    ("CF85-IADS-Comms-Sangerhausen", COMMS, 51.472, 11.297),
    ("CF85-IADS-Comms-Halle", COMMS, 51.495, 11.985),
    ("CF85-IADS-Comms-Leipzig", COMMS, 51.350, 12.390),
    ("CF85-IADS-Comms-Dessau", COMMS, 51.845, 12.260),
    ("CF85-IADS-Comms-Wittenberg", COMMS, 51.875, 12.660),
    ("CF85-IADS-Comms-Torgau", COMMS, 51.570, 13.020),
    ("CF85-IADS-Comms-Juterbog", COMMS, 52.000, 13.090),
    ("CF85-IADS-Comms-Zossen", COMMS, 52.217, 13.449),
    ("CF85-IADS-Comms-Magdeburg", COMMS, 52.140, 11.655),
    ("CF85-IADS-Power-Lippendorf", POWER, 51.178, 12.372),
    ("CF85-IADS-Power-Vockerode", POWER, 51.846, 12.355),
    ("CF85-IADS-Power-Zschornewitz", POWER, 51.716, 12.404),
    ("CF85-IADS-Power-Erfurt", POWER, 50.990, 11.070),
    ("CF85-IADS-Power-Ludwigsfelde", POWER, 52.300, 13.250),
    ("CF85-IADS-Power-Magdeburg", POWER, 52.100, 11.660),
)

#: (route name, start control point, corridor towns as (lat, lon), end control
#: point). Only the end points bind a route to its control points.
ROADS: tuple[tuple[str, str, tuple[tuple[float, float], ...], str], ...] = (
    # NATO's rear.
    ("CF85 Road Bitburg - Spangdahlem", "Bitburg", ((49.967, 6.525),), "Spangdahlem"),
    (
        "CF85 Road Norvenich - Bitburg",
        "Norvenich",
        ((50.660, 6.787), (50.437, 6.650), (50.207, 6.424)),
        "Bitburg",
    ),
    (
        "CF85 Road Spangdahlem - Hahn",
        "Spangdahlem",
        ((49.985, 6.890), (49.916, 7.067)),
        "Hahn",
    ),
    ("CF85 Road Pferdsfeld - Hahn", "Pferdsfeld", ((49.944, 7.408),), "Hahn"),
    (
        "CF85 Road Hahn - Frankfurt",
        "Hahn",
        ((49.983, 7.523), (49.967, 7.895), (50.000, 8.271), (49.995, 8.412)),
        "Frankfurt",
    ),
    ("CF85 Road Ramstein - Sembach", "Ramstein", ((49.444, 7.769),), "Sembach"),
    (
        "CF85 Road Sembach - Frankfurt",
        "Sembach",
        ((49.746, 8.116), (50.000, 8.271), (49.995, 8.412)),
        "Frankfurt",
    ),
    (
        "CF85 Road Frankfurt - Fulda",
        "Frankfurt",
        ((50.133, 8.917), (50.202, 9.189), (50.349, 9.526)),
        "Fulda",
    ),
    (
        "CF85 Road Frankfurt - Fritzlar",
        "Frankfurt",
        ((50.336, 8.755), (50.584, 8.678), (50.810, 8.771), (50.901, 9.187)),
        "Fritzlar",
    ),
    (
        "CF85 Road Frankfurt - Giebelstadt",
        "Frankfurt",
        ((49.977, 9.152), (49.845, 9.603), (49.792, 9.953)),
        "Giebelstadt",
    ),
    (
        "CF85 Road Giebelstadt - Schweinfurt",
        "Giebelstadt",
        ((49.792, 9.953), (49.983, 10.097)),
        "Schweinfurt",
    ),
    (
        "CF85 Road Fulda - Fritzlar",
        "Fulda",
        ((50.868, 9.707), (51.030, 9.404)),
        "Fritzlar",
    ),
    # The three crossings.
    (
        "CF85 Road Fulda - Haina (Fulda Gap)",
        "Fulda",
        ((50.672, 9.766), (50.715, 9.951), (50.811, 10.233), (50.975, 10.320)),
        "Haina",
    ),
    (
        "CF85 Road Fritzlar - Obermehler (Werra)",
        "Fritzlar",
        ((51.130, 9.548), (51.188, 10.053), (51.208, 10.453)),
        OBERMEHLER,
    ),
    (
        "CF85 Road Schweinfurt - Meiningen",
        "Schweinfurt",
        ((50.322, 10.216), (50.430, 10.300)),
        MEININGEN,
    ),
    (
        "CF85 Road Meiningen - Erfurt",
        MEININGEN,
        ((50.609, 10.693), (50.834, 10.947)),
        "Bindersleben",
    ),
    # The Warsaw Pact's rear.
    (
        "CF85 Road Obermehler - Haina",
        OBERMEHLER,
        ((51.108, 10.647), (50.948, 10.701)),
        "Haina",
    ),
    (
        "CF85 Road Haina - Erfurt",
        "Haina",
        ((50.948, 10.701), (50.912, 10.913)),
        "Bindersleben",
    ),
    (
        "CF85 Road Erfurt - Allstedt",
        "Bindersleben",
        ((50.978, 11.029), (51.160, 11.117), (51.368, 11.292)),
        "Allstedt",
    ),
    (
        "CF85 Road Allstedt - Merseburg",
        "Allstedt",
        ((51.381, 11.600), (51.297, 11.807)),
        "Merseburg",
    ),
    (
        "CF85 Road Merseburg - Brandis (Leipzig)",
        "Merseburg",
        ((51.302, 12.221), (51.340, 12.375), (51.348, 12.536)),
        "Brandis",
    ),
    (
        "CF85 Road Merseburg - Kothen (Halle)",
        "Merseburg",
        ((51.483, 11.970), (51.629, 12.117)),
        "Kothen",
    ),
    (
        "CF85 Road Kothen - Zerbst (Dessau)",
        "Kothen",
        ((51.835, 12.246), (51.887, 12.243)),
        "Zerbst",
    ),
    (
        "CF85 Road Zerbst - Altes Lager",
        "Zerbst",
        ((51.885, 12.448), (51.866, 12.646), (51.913, 12.784), (51.993, 13.073)),
        "Altes Lager",
    ),
    (
        "CF85 Road Altes Lager - Sperenberg",
        "Altes Lager",
        ((52.090, 13.167),),
        "Sperenberg",
    ),
    (
        "CF85 Road Brandis - Holzdorf (Torgau)",
        "Brandis",
        ((51.367, 12.738), (51.560, 13.005), (51.733, 13.044)),
        "Holzdorf",
    ),
    (
        "CF85 Road Mahlwinkel - Kothen (Magdeburg)",
        "Mahlwinkel",
        ((52.248, 11.628), (52.131, 11.640), (52.019, 11.737), (51.906, 11.775)),
        "Kothen",
    ),
)

# --- Placement tolerances ------------------------------------------------------
MIN_OFFSET_M = 3000.0
MAX_OFFSET_M = 15000.0
STEP_M = 500.0
BEARING_STEP_DEG = 15
LATERAL_OFFSETS_M = (0.0, 500.0, -500.0, 1000.0, -1000.0)
MIN_SEPARATION_M = 900.0
NEAR_OFFSET_M = 6000.0
#: A marker placed "at" a named spot may move this far to find clear land.
AT_SEARCH_M = 3000.0
AT_STEP_M = 250.0
FOB_MIN_OFFSET_M = 800.0
#: Clear of the 3,000 m capture zone, with margin.
MOTORPOOL_MIN_OFFSET_M = 3500.0


def _theater() -> Any:
    """The GermanyCW theatre, loaded only for its landmap."""
    from game import persistency
    from game.campaignloader.campaign import Campaign

    persistency.setup(str(Path.home() / "Saved Games" / "DCS"), False, 0)
    return Campaign.from_file(SOURCE_YAML).load_theater(advanced_iads=False)


def _xy(terrain: Any, lat: float, lon: float) -> Point:
    return Point.from_latlng(LatLng(lat, lon), terrain)


def _in_sector(position: Point) -> bool:
    ll = position.latlng()
    return (
        SECTOR_LAT[0] <= ll.lat <= SECTOR_LAT[1]
        and SECTOR_LON[0] <= ll.lng <= SECTOR_LON[1]
    )


class Placer:
    """Finds clear land for an added marker, deterministically.

    "Clear" is the landmap's own answer: inside an inclusion zone and outside
    every exclusion zone. Where no clear point is in reach the marker falls back
    to inclusion-only ground, and the report names it.
    """

    def __init__(self, theater: Any, taken: list[Point]):
        self.theater = theater
        self.taken = taken
        self.relaxed: list[str] = []

    def _free(self, candidate: Point) -> bool:
        return all(
            candidate.distance_to_point(other) >= MIN_SEPARATION_M
            for other in self.taken
        )

    def _pick(self, name: str, passes: Iterable[tuple[list[Point], bool]]) -> Point:
        for candidates, relaxed in passes:
            for candidate in candidates:
                if not self.theater.is_on_land(candidate, ignore_exclusion=relaxed):
                    continue
                if self._free(candidate):
                    if relaxed:
                        self.relaxed.append(name)
                    self.taken.append(candidate)
                    return candidate
        raise RuntimeError(f"no land for {name} within reach of its anchor")

    @staticmethod
    def _rings(
        origin: Point, start: float, stop: float = MAX_OFFSET_M, step: float = STEP_M
    ) -> list[Point]:
        found = []
        radius = start
        while radius <= stop:
            for bearing in range(0, 360, BEARING_STEP_DEG):
                found.append(origin.point_from_heading(bearing, radius))
            radius += step
        return found

    def ring(self, name: str, origin: Point, start: float = MIN_OFFSET_M) -> Point:
        rings = self._rings(origin, start)
        return self._pick(name, ((rings, False), (rings, True)))

    def near(self, name: str, origin: Point, start: float = MIN_OFFSET_M) -> Point:
        close = self._rings(origin, start, NEAR_OFFSET_M)
        far = self._rings(origin, NEAR_OFFSET_M + STEP_M)
        return self._pick(
            name, ((close, False), (close, True), (far, False), (far, True))
        )

    def at(self, name: str, spot: Point) -> Point:
        candidates = [spot] + self._rings(spot, AT_STEP_M, AT_SEARCH_M, AT_STEP_M)
        return self._pick(name, ((candidates, False), (candidates, True)))

    def axis(self, name: str, airport: Airport) -> Point:
        heading = float(airport.runways[0].heading)
        candidates = []
        distance = MIN_OFFSET_M
        while distance <= MAX_OFFSET_M:
            for along in (heading, heading + 180.0):
                centre = airport.position.point_from_heading(along, distance)
                for lateral in LATERAL_OFFSETS_M:
                    candidates.append(centre.point_from_heading(along + 90.0, lateral))
            distance += STEP_M
        candidates += self._rings(airport.position, MIN_OFFSET_M)
        return self._pick(name, ((candidates, False), (candidates, True)))


def _country(mission: Mission, block: str) -> Any:
    country = mission.country(
        MizCampaignLoader.BLUE_COUNTRY.name
        if block == BLUE_BLOCK
        else MizCampaignLoader.RED_COUNTRY.name
    )
    assert country is not None
    return country


def _is_white(zone: TriggerZone) -> bool:
    return zone.color[1] == 1 and zone.color[2] == 1 and zone.color[3] == 1


def _is_blue(zone: TriggerZone) -> bool:
    return zone.color[1] == 0 and zone.color[2] == 0 and zone.color[3] == 1


def _contains(parent: TriggerZone, point: Point) -> bool:
    radius = getattr(parent, "radius", 0.0)
    return parent.position.distance_to_point(point) < radius


def _strip(mission: Mission) -> None:
    """Keep the map, its settings and the sector's scenery sets; drop the rest."""
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            for groups in (
                country.vehicle_group,
                country.ship_group,
                country.plane_group,
                country.helicopter_group,
                country.static_group,
            ):
                groups.clear()
    zones = mission.triggers._zones
    parents = [z for z in zones if _is_blue(z) and _in_sector(z.position)]
    kept: list[TriggerZone] = list(parents)
    for zone in zones:
        if _is_white(zone) and any(_contains(p, zone.position) for p in parents):
            kept.append(zone)
    ctld = [
        z
        for z in zones
        if any(z.name.startswith(f"{name} CTLD") for name in BLUE_AIRFIELDS)
        or any(z.name.startswith(f"{name} CTLD") for name in RED_AIRFIELDS)
    ]
    mission.triggers._zones = [z for z in zones if z in kept or z in ctld]
    print(f"scenery: kept {len(parents)} target sets, {len(kept) - len(parents)} parts")
    # pydcs reads the source's bare 'theatre' entry as a resource and writes it twice.
    mission.map_resource.binary_files = [
        f for f in mission.map_resource.binary_files if f["respath"] != "theatre"
    ]


def _set_ownership(mission: Mission) -> None:
    print("airfield ownership:")
    for airport in mission.terrain.airport_list():
        airport.unlimited_aircrafts = False
        if airport.name in BLUE_AIRFIELDS:
            airport.set_blue()
        elif airport.name in RED_AIRFIELDS:
            airport.set_red()
            # The invert flag: an inverted game hands this field to the player.
            airport.unlimited_aircrafts = True
        else:
            airport.set_neutral()
            # Neutral WITH dynamic spawn reads as a red control point here.
            airport.dynamic_spawn = False
    for name in BLUE_AIRFIELDS + RED_AIRFIELDS:
        if name not in mission.terrain.airports:
            raise RuntimeError(f"{name} is not an airfield on this terrain")
        side = "BLUE" if name in BLUE_AIRFIELDS else "RED"
        print(f"  {name:<28} {side}")


def _add_vehicle(
    mission: Mission, block: str, name: str, position: Point, unit_type: Any
) -> Any:
    group = mission.vehicle_group(
        country=_country(mission, block), name=name, _type=unit_type, position=position
    )
    # Markers are read for their type and position only; they are never driven.
    for point in group.points:
        point.action = PointAction.OffRoad
        point.speed = 0
    return group


def _report(name: str, position: Point, anchor: str = "") -> None:
    ll = position.latlng()
    print(f"  {name:<36} ({ll.lat:7.3f}, {ll.lng:7.3f})  {anchor}")


def _origin(mission: Mission, anchor: Anchor) -> Point:
    if isinstance(anchor, str):
        for name, lat, lon in FOBS:
            if name == anchor:
                return _xy(mission.terrain, lat, lon)
        return mission.terrain.airports[anchor].position
    return _xy(mission.terrain, *anchor)


def _start(anchor: Anchor) -> float:
    if not isinstance(anchor, str):
        return 0.0
    # A FOB has no runway strip to keep clear of.
    return FOB_MIN_OFFSET_M if any(anchor == f[0] for f in FOBS) else MIN_OFFSET_M


def _place(
    mission: Mission, placer: Placer, name: str, anchor: Anchor, how: str, start: float
) -> Point:
    origin = _origin(mission, anchor)
    if how == "axis":
        assert isinstance(anchor, str)
        return placer.axis(name, mission.terrain.airports[anchor])
    if how == "at":
        return placer.at(name, origin)
    if how == "near":
        return placer.near(name, origin, start)
    return placer.ring(name, origin, start)


def _author_land(mission: Mission, placer: Placer) -> None:
    print("\nforward operating bases:")
    for name, lat, lon in FOBS:
        position = _xy(mission.terrain, lat, lon)
        if not placer.theater.is_on_land(position):
            raise RuntimeError(f"{name} is not on clear land")
        placer.taken.append(position)
        group = _add_vehicle(mission, RED_BLOCK, name, position, Unarmed.SKP_11)
        group.late_activation = True  # the invert flag
        _report(name, position)

    print("\nadded markers:")
    for name, anchor, unit_type, block, how in ADDED_MARKERS:
        start = _start(anchor)
        position = _place(mission, placer, name, anchor, how, start)
        _add_vehicle(mission, block, name, position, unit_type)
        _report(name, position, str(anchor))

    for name, spot in SCUD_SITES:
        position = placer.at(name, _xy(mission.terrain, *spot))
        _add_vehicle(mission, RED_BLOCK, name, position, MissilesSS.Scud_B)
        _report(name, position)

    print("\neconomy:")
    for name, anchor, static_type, block, how in ADDED_STATICS:
        start = _start(anchor)
        if static_type is Fortification.Garage_A:
            # A motorpool's parked armor inside a capture zone blocks the capture.
            start = max(start, MOTORPOOL_MIN_OFFSET_M)
        position = _place(mission, placer, name, anchor, how, start)
        mission.static_group(
            country=_country(mission, block),
            name=name,
            _type=static_type,
            position=position,
        )
        _report(name, position, str(anchor))

    print("\nSoviet IADS:")
    for name, static_type, lat, lon in IADS_NODES:
        position = placer.at(name, _xy(mission.terrain, lat, lon))
        mission.static_group(
            country=_country(mission, RED_BLOCK),
            name=name,
            _type=static_type,
            position=position,
        )
        _report(name, position)


def _author_roads(mission: Mission) -> None:
    from campaign_routes import draw

    # MizCampaignLoader reads route groups from this one country only.
    country = mission.country(CombinedJointTaskForcesBlue.name)
    print("\nroads:")
    for name, start, corridor, end in ROADS:
        first = _origin(mission, start)
        points = [(first.x, first.y)]
        for lat, lon in corridor:
            p = _xy(mission.terrain, lat, lon)
            points.append((p.x, p.y))
        last = _origin(mission, end)
        points.append((last.x, last.y))
        draw(mission, country, "route", name, points)
        group = country.vehicle_group[-1]
        # An On Road first leg the editor cannot path from a runway crashes it.
        group.points[0].action = PointAction.OffRoad
        group.points[-1].action = PointAction.OffRoad
        print(f"  {name} ({len(points)} waypoints)")


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"missing source miz: {SOURCE}")

    mission = Mission()
    mission.load_file(str(SOURCE))
    print(f"loaded {SOURCE.name} ({mission.terrain.name})\n")
    theater = _theater()

    _strip(mission)
    _set_ownership(mission)
    taken = [mission.terrain.airports[n].position for n in BLUE_AIRFIELDS]
    taken += [mission.terrain.airports[n].position for n in RED_AIRFIELDS]
    placer = Placer(theater, taken)
    _author_land(mission, placer)
    _author_roads(mission)

    if placer.relaxed:
        print("\nplaced on inclusion-only ground (no fully clear point in reach):")
        for name in placer.relaxed:
            print(f"  {name}")

    mission.save(str(DEST))
    print(f"\nwrote {DEST.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
