"""What each airframe's cartridge carries, for the DTC tab (§74, §102).

One row per ``DtcOptions`` section flag, with what it does on each jet that has it.
An airframe missing from a row's ``on`` does not carry that section, and the tab does
not offer it.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.missiongenerator.dtc.apache import APACHE_UNIT_TYPE
from game.missiongenerator.dtc.hornet import HORNET_UNIT_TYPE
from game.missiongenerator.dtc.tomcat import TOMCAT_UNIT_TYPE
from game.missiongenerator.dtc.viper import VIPER_UNIT_TYPE

NAVIGATION = "Navigation"
PICTURE = "Situation picture"
WEAPONS = "Weapons and defense"
COMMS = "Comms"
GROUPS = (NAVIGATION, PICTURE, WEAPONS, COMMS)


@dataclass(frozen=True)
class Section:
    attr: str
    label: str
    group: str
    #: DCS type id -> what the section does on that jet.
    on: dict[str, str]


SECTIONS: tuple[Section, ...] = (
    Section(
        "route",
        "Flight plan",
        NAVIGATION,
        {
            HORNET_UNIT_TYPE: "The route as named waypoints on sequence 1, with the"
            " planned leg speeds and times, and the package's lane from the IP over"
            " the target to the split on the SA page.",
            VIPER_UNIT_TYPE: "The route as steerpoints from 1 (20 at most) with times"
            " on target. Saved points and support anchors follow it, up to 24."
            " A CAS or SEAD flight's working area is an HSD box, tagged CAS or SD.",
            TOMCAT_UNIT_TYPE: "The route on flight plan 2 with its times. Plan 1 stays"
            " the mission editor's own.",
            APACHE_UNIT_TYPE: "The route as W-points on route ALPHA, with leg speeds"
            " and times.",
        },
    ),
    Section(
        "saved_points",
        "Saved points",
        NAVIGATION,
        {
            HORNET_UNIT_TYPE: "After the route, on sequence 2; orbits join the SA page's"
            " CAP list. Needs Flight plan on.",
            VIPER_UNIT_TYPE: "After the route, before the support anchors, on"
            " sequence 2. IPs and targets get their HSD symbols; orbits are HSD boxes."
            " Needs Flight plan on.",
            TOMCAT_UNIT_TYPE: "Flight plan 3, named SAVED. IPs and targets carry the"
            " jet's XIP / XST codes; orbits are plot-line boxes.",
            APACHE_UNIT_TYPE: "After the route as W-points, on route BRAVO; orbits are"
            " TSD areas. Needs Flight plan on.",
        },
    ),
    Section(
        "nav_aids",
        "Recovery aids",
        NAVIGATION,
        {
            HORNET_UNIT_TYPE: "Pre-tunes the recovery TACAN (the boat's whole card on"
            " a carrier flight), sets the FPAS home waypoint, makes the bullseye"
            " the air-to-air waypoint, and lists the boats, your home, arrival and"
            " divert fields, then the map's other TACANs nearest your route, 10 in"
            " all.",
        },
    ),
    Section(
        "destinations",
        "Recovery fields",
        NAVIGATION,
        {
            VIPER_UNIT_TYPE: "Friendly fields and boats as Destination steerpoints,"
            " the briefed divert first and the enemy field you are working over"
            " next to it. The tags naming the HSD lines take up to 8 of the 19"
            " slots, and stay when this is off.",
        },
    ),
    Section(
        "flot_and_zones",
        "Front line",
        PICTURE,
        {
            HORNET_UNIT_TYPE: "On the SA page. Ticked to start on CAS flights only.",
            VIPER_UNIT_TYPE: "An HSD line: 4 points when National borders are"
            " drawn (3 beside a CAS flight's working-area box), otherwise what"
            " your drawings and the tanker box leave. Ticked to start on CAS"
            " flights only.",
            TOMCAT_UNIT_TYPE: "As a plot line.",
            APACHE_UNIT_TYPE: "As a TSD line.",
        },
    ),
    Section(
        "borders",
        "National borders",
        PICTURE,
        {
            HORNET_UNIT_TYPE: "Land borders within 40 NM of your route on the SA"
            " page: the nearest dashed, the next solid unless the front line"
            " takes it.",
            VIPER_UNIT_TYPE: "Land borders within 40 NM of your route as HSD lines,"
            " the nearest two first, 12 points at most. They come before everything else on the HSD"
            " but your drawings.",
        },
    ),
    Section(
        "friendly_orbits",
        "Own orbit, tankers and AWACS",
        PICTURE,
        {
            HORNET_UNIT_TYPE: "Racetracks on the SA page, this flight's own first,"
            " and a box on the tanker you can take gas from when no border takes"
            " the dashed line.",
            VIPER_UNIT_TYPE: "Steerpoints after the saved points, and a box on the"
            " tanker you can use.",
            TOMCAT_UNIT_TYPE: "Reference points and a plot-line box on the tanker.",
            APACHE_UNIT_TYPE: "A TSD box on the tanker.",
        },
    ),
    Section(
        "threat_rings",
        "Known SAM sites",
        PICTURE,
        {
            HORNET_UNIT_TYPE: "Threat rings on the SA page for the sites your side"
            " has engaged.",
            VIPER_UNIT_TYPE: "Threat rings on the HSD for the sites your side has"
            " engaged.",
            TOMCAT_UNIT_TYPE: "Reference points for the sites your side has engaged;"
            " the widest ring is the hostile area that sets the threat axis.",
            APACHE_UNIT_TYPE: "Target points on the TSD for the sites your side has"
            " engaged.",
        },
    ),
    Section(
        "drawings",
        "Your drawings",
        PICTURE,
        {
            HORNET_UNIT_TYPE: "Your lines and areas on the SA page.",
            VIPER_UNIT_TYPE: "Your lines and areas on HSD line sets 2-4.",
            TOMCAT_UNIT_TYPE: "Your lines and areas as plot lines on flight plan 3.",
            APACHE_UNIT_TYPE: "Your lines on the TSD, split into 4-corner pieces;"
            " a 4-corner area as a TSD area.",
        },
    ),
    Section(
        "jdam_targets",
        "Pre-planned JDAM targets",
        WEAPONS,
        {
            TOMCAT_UNIT_TYPE: "Each JDAM station gets its target as a pre-planned"
            " aimpoint with the run-in from the IP.",
        },
    ),
    Section(
        "roe_table",
        "ROE air target table",
        WEAPONS,
        {
            VIPER_UNIT_TYPE: "Aircraft families only your side flies are declared"
            " FRIENDLY, only the enemy's HOSTILE, shared ones UNKNOWN.",
        },
    ),
    Section(
        "countermeasures",
        "Countermeasure programs",
        WEAPONS,
        {
            VIPER_UNIT_TYPE: "MAN 1 flares only, MAN 5 chaff only, and the jet's"
            " own auto program for every threat: AUTO 2, none for search radars"
            " and AWACS. Set the CMDS knob to STBY before the cartridge loads.",
        },
    ),
    Section(
        "comms",
        "Comms",
        COMMS,
        {
            HORNET_UNIT_TYPE: "Names the radio presets after what they tune: your"
            " flight, AWACS and tankers by callsign, then PKG, JTAC, DEP, ARR, DVT.",
            TOMCAT_UNIT_TYPE: "The package's other flights on the TIS send-to list.",
        },
    ),
)


def sections_for(dcs_id: str) -> list[Section]:
    """The sections this airframe's cartridge carries, in display order."""
    return [section for section in SECTIONS if dcs_id in section.on]
