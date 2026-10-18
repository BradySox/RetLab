"""Build resources/campaigns/desert_aladeen_h3_front.miz from Starfire's Desert Aladeen.

Iraq - Desert Aladeen: The H-3 Front. Starfire's `operation_desert_aladeen.miz` is the
untouched source (it stays a test standard); this tool writes a separate campaign miz:

- Ownership: red takes blue's Baghdad and Al-Salam plus Al-Sahra, Mosul, Al-Kut, Al-Asad,
  Al-Taquddum and Kharg; blue holds the three H-3 strips and an off-map rear in Jordan
  (the map has no heavy stands west of Baghdad, so the E-3/tanker/B-1B wing flies in).
- Red's first rung is FOB Wadi Hauran, about 85 mi east of H-3 (the DM wanted 75-100 mi
  between the sides at the start); H-2 stays unowned between them.
- Base defenses and economy markers at every new base, and a north-west target set.

Every placed group is a band marker (`MizCampaignLoader` vocabulary): the unit type
picks the band, the faction fills the system. Coordinates are mission x (north) / y
(east) in metres, on open ground at least 250 m from the landmap's exclusion zones (a
SAM marker by its widest layout, so no launcher lands in a town or the sea) and at
least 3.5 km from any airfield reference point (1.2 km on Kharg).
Design note: docs/dev/design/retlab-desert-aladeen-h3-campaign-notes.md.

Usage: python tools/build_desert_aladeen_h3_miz.py
"""

from __future__ import annotations

from pathlib import Path

from dcs.mapping import Point
from dcs.mission import Mission
from dcs.planes import F_15C
from dcs.statics import Fortification, Warehouse
from dcs.unittype import StaticType, VehicleType
from dcs.vehicles import AirDefence, Armor, MissilesSS, Unarmed

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "resources/campaigns/operation_desert_aladeen.miz"
DST = REPO / "resources/campaigns/desert_aladeen_h3_front.miz"

BLUE_COUNTRY = "Combined Joint Task Forces Blue"
RED_COUNTRY = "Combined Joint Task Forces Red"

BLUE_AIRFIELDS = [
    "H-3 Main Airbase",
    "H-3 Northwest Airbase",
    "H-3 Southwest Airbase",
]
#: Starfire's four red fields (Kirkuk, Erbil, Qayyarah, Sulaimaniyah) stay red.
RED_AIRFIELDS = [
    "Baghdad International Airport",
    "Al-Salam Airbase",
    "Al-Sahra Airport",
    "Mosul International Airport",
    "Al-Kut Airport",
    "Al-Asad Airbase",
    "Al-Taquddum Airport",
    "Kharg Airfield",
]

#: 10 km inside Iraq on the Jordan border. Jordan is a neutral under §98, so a C-130J
#: that spawns inside it is engaged after 180 s.
OFF_MAP_REAR = ("Coalition Rear (Jordan)", (-60000.0, -478000.0))
RED_FOB = ("FOB Wadi Hauran", (42000.0, -298800.0))
#: Without a zone the FOB is the nearest control point to the Al-Qaim complex 56 mi
#: north, and taking the first rung would depopulate it. The zone keeps the FOB to its
#: own furniture (all within 2.5 mi); Al-Qaim falls to Al-Asad.
RED_FOB_ZONE_RADIUS_M = 6000

#: Marker name prefix -> the band-marker type the loader reads.
VEHICLE_MARKERS: dict[str, type[VehicleType]] = {
    "PATRIOT": AirDefence.Patriot_ln,
    "NASAMS": AirDefence.NASAMS_LN_C,
    "LORAD": AirDefence.S_300PS_5P85C_ln,
    "MERAD": AirDefence.x_5p73_s_125_ln,
    "EWR": AirDefence.x_1L13_EWR,
    "ARMOR": Armor.M_1_Abrams,
    "SCUD": MissilesSS.Scud_B,
}
STATIC_MARKERS: dict[str, type[StaticType]] = {
    "AMMO": Warehouse._Ammunition_depot,
    "STRIKE": Fortification.Tech_combine,
}

#: Base defenses and economy at every base that changed hands.
BASE_MARKERS: list[tuple[str, float, float]] = [
    ("PATRIOT H-3", -23566, -412685),
    ("SHORAD H-3 Main", -20384, -416003),
    ("AAA H-3 Main 1", -25566, -415721),
    ("AAA H-3 Main 2", -19807, -417817),
    ("ARMOR H-3 Main 1", -21685, -414016),
    ("ARMOR H-3 Main 2", -27779, -415649),
    ("AMMO H-3 Main", -24434, -414261),
    ("NASAMS H-3 Northwest", -2090, -435419),
    ("SHORAD H-3 Northwest", -5747, -436648),
    ("AAA H-3 Northwest", -3286, -432419),
    ("ARMOR H-3 Northwest", -3750, -436632),
    ("SHORAD H-3 Southwest", -48479, -435330),
    ("AAA H-3 Southwest", -48190, -433097),
    ("LORAD Al-Asad", 66947, -171043),
    ("MERAD Al-Asad", 67319, -165901),
    ("EWR Al-Asad", 67713, -160116),
    ("SHORAD Al-Asad", 63069, -162004),
    ("AAA Al-Asad 1", 60159, -162159),
    ("AAA Al-Asad 2", 61479, -169643),
    ("ARMOR Al-Asad", 65582, -163151),
    ("AMMO Al-Asad", 65517, -167611),
    ("STRIKE Al-Asad", 54757, -162401),
    ("MERAD Al-Taquddum", 6163, -58574),
    ("SHORAD Al-Taquddum", 13510, -61226),
    ("AAA Al-Taquddum 1", 16117, -58133),
    ("AAA Al-Taquddum 2", 5917, -58133),
    ("ARMOR Al-Taquddum", 11598, -63302),
    ("AMMO Al-Taquddum", 11091, -61469),
    ("STRIKE Al-Taquddum", 14780, -52566),
    ("LORAD Al-Sahra", 155744, -69683),
    ("MERAD Al-Sahra", 160383, -67434),
    ("SHORAD Al-Sahra", 161633, -61805),
    ("AAA Al-Sahra 1", 160044, -59362),
    ("AAA Al-Sahra 2", 154222, -64247),
    ("ARMOR Al-Sahra", 161896, -64555),
    ("AMMO Al-Sahra", 158002, -66729),
    ("STRIKE Al-Sahra", 157133, -54805),
    ("MERAD Mosul", 333361, -96294),
    ("SHORAD Mosul", 338746, -97568),
    ("AAA Mosul 1", 345240, -95371),
    ("AAA Mosul 2", 334944, -92472),
    ("ARMOR Mosul", 339269, -99571),
    ("AMMO Mosul", 335639, -97285),
    ("STRIKE Mosul", 349411, -88100),
    ("MERAD Al-Kut", -92232, 143282),
    ("SHORAD Al-Kut", -84951, 138850),
    ("AAA Al-Kut 1", -82621, 141186),
    ("AAA Al-Kut 2", -88643, 145724),
    ("ARMOR Al-Kut", -87613, 138113),
    ("AMMO Al-Kut", -90430, 141572),
    ("STRIKE Al-Kut", -78838, 144497),
    ("SHORAD Kharg", -432224, 588463),
    ("LORAD Kharg", -433388, 588756),
    ("AAA Kharg", -431816, 588514),
    ("SHORAD Wadi Hauran", 43250, -296635),
    ("AAA Wadi Hauran", 40121, -299484),
    ("ARMOR Wadi Hauran 1", 40974, -301619),
    ("ARMOR Wadi Hauran 2", 43750, -301831),
    ("AMMO Wadi Hauran", 40500, -296202),
]

#: The north-west target set (10 strike targets, 6 Scud batteries, 6 SAM sites).
NORTH_WEST_MARKERS: list[tuple[str, float, float]] = [
    ("STRIKE Tal Afar Garrison HQ", 350642, -159112),
    ("STRIKE Tal Afar Fuel Depot", 345615, -152051),
    ("STRIKE Sinjar Signals Station", 348579, -214847),
    ("STRIKE Rabia Border Post", 396553, -186446),
    ("STRIKE Badush Munitions Plant", 350211, -111546),
    ("STRIKE Al-Qaim Superphosphate Works", 132737, -290970),
    ("STRIKE Al-Qaim Rail Yard", 128737, -281840),
    ("STRIKE Rawah Bridge Depot", 138236, -207858),
    ("STRIKE Haditha Dam Power Station", 108386, -170153),
    ("STRIKE Baaj Supply Depot", 313561, -222056),
    ("SCUD Sinjar West", 342533, -233033),
    ("SCUD Baaj", 302934, -211836),
    ("SCUD Hatra", 264397, -145070),
    ("SCUD Al-Qaim", 121398, -263674),
    ("SCUD Wadi Tharthar", 206093, -119120),
    ("SCUD Tal Afar South", 329209, -161473),
    ("LORAD Tal Afar", 343754, -165575),
    ("LORAD Al-Qaim", 135422, -276788),
    ("MERAD Sinjar", 339265, -201663),
    ("MERAD Rabia", 387542, -182249),
    ("MERAD Haditha", 96192, -165718),
    ("MERAD Hatra", 256311, -131660),
]


def marker_type(name: str) -> type[VehicleType] | type[StaticType]:
    prefix = name.split()[0]
    blue = " H-3 " in f" {name} "
    if prefix == "SHORAD":
        return AirDefence.M1097_Avenger if blue else AirDefence.rapier_fsa_launcher
    if prefix == "AAA":
        return AirDefence.Vulcan if blue else AirDefence.ZSU_23_4_Shilka
    if prefix in VEHICLE_MARKERS:
        return VEHICLE_MARKERS[prefix]
    return STATIC_MARKERS[prefix]


def build() -> None:
    mission = Mission()
    mission.load_file(str(SRC))
    blue = mission.country(BLUE_COUNTRY)
    red = mission.country(RED_COUNTRY)
    if blue is None or red is None:
        raise RuntimeError(f"{SRC} lacks a CJTF country block")

    airports = {a.name: a for a in mission.terrain.airport_list()}
    for name in BLUE_AIRFIELDS:
        airports[name].set_blue()
    for name in RED_AIRFIELDS:
        airports[name].set_red()

    def point(x: float, y: float) -> Point:
        return Point(x, y, mission.terrain)

    rear_name, rear_xy = OFF_MAP_REAR
    mission.flight_group_inflight(
        country=blue,
        name=rear_name,
        aircraft_type=F_15C,
        position=point(*rear_xy),
        altitude=6000,
    )
    fob_name, fob_xy = RED_FOB
    mission.vehicle_group(
        country=red, name=fob_name, _type=Unarmed.SKP_11, position=point(*fob_xy)
    )
    mission.triggers.add_triggerzone(
        point(*fob_xy),
        radius=RED_FOB_ZONE_RADIUS_M,
        name=fob_name,
        color={1: 1, 2: 0, 3: 0, 4: 0.15},
        properties={1: {"key": "PROPERTY_1", "value": fob_name}},
    )

    # Red block for every marker: it is the coalition-agnostic block, so a marker
    # binds the nearest control point of either side (the H-3 ones become blue's).
    for name, x, y in BASE_MARKERS + NORTH_WEST_MARKERS:
        kind = marker_type(name)
        if issubclass(kind, StaticType):
            mission.static_group(
                country=red, name=name, _type=kind, position=point(x, y)
            )
        else:
            mission.vehicle_group(
                country=red, name=name, _type=kind, position=point(x, y)
            )

    # Supply routes and sea lanes are drawn in the .miz; keep the drawn ones.
    from campaign_routes import carry_route_groups

    carry_route_groups(mission, DST)
    mission.save(str(DST))
    print(
        f"Wrote {DST}: {len(BLUE_AIRFIELDS)} blue + {len(RED_AIRFIELDS)} new red "
        f"airfields, {len(BASE_MARKERS)} base and {len(NORTH_WEST_MARKERS)} "
        "north-west markers"
    )


if __name__ == "__main__":
    build()
