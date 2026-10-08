"""Air-defence system catalog for the Threat Intel Brief kneeboard.

One entry per system, keyed by the DCS unit ids of its radars and launchers.
Ceilings are each missile's ``H_max`` in
``CoreMods\\tech\\TechWeaponPack\\Database\\Weapons``; RWR symbols are from
``Scripts\\Aircrafts\\_Common\\Cockpit\\AN_ALR_SymbolsBase.lua``. The "how to beat
it" lines follow the squadron's Soviet SAMs guide; a system that guide does not
cover carries no line rather than unchecked advice. Engagement and search ranges
are not here: the brief reads them live from the site.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from dcs.vehicles import AirDefence


@dataclass(frozen=True)
class ThreatReference:
    name: str
    guidance: str
    ceiling_ft: Optional[int]
    rwr: str
    beat: str
    approximate_ceiling: bool = False


_SA2 = ThreatReference(
    'SA-2 "Guideline"',
    "Radar",
    82000,
    "2 (S)",
    "The missile is big and cannot turn hard. On a launch put the site at your 3 or "
    "9 o'clock, chaff, and pull hard as it gets close. Below about 1,000 ft its "
    "radar loses you.",
)
_SA3 = ThreatReference(
    'SA-3 "Goa"',
    "Radar",
    59000,
    "3 (S)",
    "Short range: route around it. On a launch turn side-on, chaff, and pull late. "
    "It sees low flyers better than the SA-2.",
)
_SA5 = ThreatReference(
    'SA-5 "Gammon"',
    "Radar",
    131000,
    "5 (TS)",
    "Slow to react and the missile is huge: turn side-on and dive. Below about "
    "1,000 ft near the site it cannot shoot. Keep tankers and AWACS outside its ring.",
)
_SA6 = ThreatReference(
    'SA-6 "Gainful"',
    "Radar",
    26000,
    "6",
    "Stay above 26,000 ft and it cannot reach you. On a launch turn side-on, chaff "
    "hard, and get low behind terrain. Its only radar is the Straight Flush: HARM it.",
)
_SA8 = ThreatReference(
    'SA-8 "Gecko"',
    "Radar",
    16400,
    "8",
    "Stay above 16,400 ft or more than 6 NM away. On a launch turn side-on and chaff.",
)
_SA10 = ThreatReference(
    'SA-10 "Grumble"',
    "Radar",
    82000,
    "10 (BB, CS, TS)",
    "Do not enter the ring without a SEAD plan. If you must, fly very low behind "
    "terrain; the Clam Shell hunts low flyers. HARMs on the radars open the door.",
)
_SA11 = ThreatReference(
    'SA-11 "Gadfly"',
    "Radar",
    72000,
    "11 (SD)",
    "Altitude will not save you. Stay outside the ring, fly low behind terrain, or "
    "bring SEAD. Every launcher has its own radar and needs its own HARM or bomb.",
)
_SA9 = ThreatReference(
    'SA-9 "Gaskin"',
    "Heat",
    11500,
    "none",
    "No warning. Stay above 11,500 ft. Down low, flare over troops and do not hang "
    "around.",
)
_SA13 = ThreatReference(
    'SA-13 "Gopher"',
    "Heat",
    11500,
    "13 (ranging radar only)",
    "No launch warning: 13 means one is near, not a missile in the air. Stay above "
    "11,500 ft; if you must go low, flare early and often.",
)
_SA15 = ThreatReference(
    'SA-15 "Gauntlet"',
    "Radar",
    19700,
    "15",
    "Stay above 19,700 ft and outside 6.5 NM. It shoots down HARMs and JDAMs: use "
    "several at once or stand off outside its range.",
)
_SA19 = ThreatReference(
    'SA-19 "Grison"',
    "Radar + guns",
    11500,
    "19",
    "Stay above 11,500 ft and roll in from high. Never make low gun or rocket passes "
    "near one.",
)
_IGLA = ThreatReference(
    "SA-18 Igla MANPADS",
    "Heat",
    11500,
    "none",
    "Assume every group of enemy troops has one. Stay above 11,500 ft; on low passes "
    "flare before you reach the troops, not after the launch.",
)
_SHILKA = ThreatReference(
    'ZSU-23-4 "Shilka"',
    "Radar gun",
    6500,
    "A",
    "Harmless above about 6,500 ft. Stay high and make no low passes near it.",
    approximate_ceiling=True,
)
_HAWK = ThreatReference("MIM-23 Hawk", "Radar", 131000, "HK", "")
_PATRIOT = ThreatReference("MIM-104 Patriot", "Radar", 79500, "P", "")
_NASAMS = ThreatReference("NASAMS", "Radar", None, "NS", "")
_ROLAND = ThreatReference("Roland", "Radar", 19700, "RO", "")
_RAPIER = ThreatReference("Rapier", "Optical or radar", 9800, "RT (RP)", "")
_STINGER = ThreatReference("FIM-92 Stinger MANPADS", "Heat", None, "none", "")
_GEPARD = ThreatReference("Gepard", "Radar gun", None, "A", "")
_VULCAN = ThreatReference("M163 Vulcan", "Radar gun", None, "A", "")

_SEARCH_BEAT = (
    "Cannot shoot. It finds you for the SAMs and fighters. Hills block it: fly low "
    "behind terrain."
)


def _search_radar(name: str, rwr: str) -> ThreatReference:
    return ThreatReference(name, "Search radar", None, rwr, _SEARCH_BEAT)


_BOX_SPRING = _search_radar('1L13 "Box Spring"', "S")
_TALL_RACK = _search_radar('55G6 "Tall Rack"', "S")
_TALL_KING = _search_radar('P-14 "Tall King"', "5")
_FLAT_FACE = _search_radar('P-19 "Flat Face"', "S")
_BIG_BIRD = _search_radar('64N6E "Big Bird"', "BB")
_CLAM_SHELL = _search_radar('5N66M "Clam Shell"', "CS")
_TIN_SHIELD = _search_radar('ST-68U "Tin Shield"', "TS")
_SNOW_DRIFT = _search_radar('9S18M1 "Snow Drift"', "SD")
_DOG_EAR = _search_radar('9S80 "Dog Ear"', "DE")


_SYSTEMS: Tuple[Tuple[ThreatReference, Tuple[str, ...]], ...] = (
    (_SA2, (AirDefence.SNR_75V.id, AirDefence.S_75M_Volhov.id, AirDefence.RD_75.id)),
    (_SA3, (AirDefence.snr_s_125_tr.id, AirDefence.x_5p73_s_125_ln.id)),
    (_SA5, (AirDefence.RPC_5N62V.id, AirDefence.S_200_Launcher.id)),
    (_SA6, (AirDefence.Kub_1S91_str.id, AirDefence.Kub_2P25_ln.id)),
    (_SA8, (AirDefence.Osa_9A33_ln.id,)),
    (
        _SA10,
        (
            AirDefence.S_300PS_40B6M_tr.id,
            AirDefence.S_300PS_5H63C_30H6_tr.id,
            AirDefence.S_300PS_5P85C_ln.id,
            AirDefence.S_300PS_5P85D_ln.id,
        ),
    ),
    (_SA11, (AirDefence.SA_11_Buk_LN_9A310M1.id,)),
    (_SA9, (AirDefence.Strela_1_9P31.id,)),
    (_SA13, (AirDefence.Strela_10M3.id,)),
    (_SA15, (AirDefence.Tor_9A331.id,)),
    (_SA19, (AirDefence.x_2S6_Tunguska.id,)),
    (
        _IGLA,
        (
            AirDefence.SA_18_Igla_manpad.id,
            AirDefence.SA_18_Igla_S_manpad.id,
            AirDefence.Igla_manpad_INS.id,
            AirDefence.SA_18_Igla_comm.id,
            AirDefence.SA_18_Igla_S_comm.id,
        ),
    ),
    (_SHILKA, (AirDefence.ZSU_23_4_Shilka.id,)),
    (
        _HAWK,
        (
            AirDefence.Hawk_tr.id,
            AirDefence.Hawk_sr.id,
            AirDefence.Hawk_cwar.id,
            AirDefence.Hawk_ln.id,
        ),
    ),
    (_PATRIOT, (AirDefence.Patriot_str.id, AirDefence.Patriot_ln.id)),
    (
        _NASAMS,
        (
            AirDefence.NASAMS_Radar_MPQ64F1.id,
            AirDefence.NASAMS_LN_B.id,
            AirDefence.NASAMS_LN_C.id,
        ),
    ),
    (_ROLAND, (AirDefence.Roland_ADS.id, AirDefence.Roland_Radar.id)),
    (
        _RAPIER,
        (
            AirDefence.rapier_fsa_launcher.id,
            AirDefence.rapier_fsa_blindfire_radar.id,
            AirDefence.rapier_fsa_optical_tracker_unit.id,
        ),
    ),
    (
        _STINGER,
        (
            AirDefence.Soldier_stinger.id,
            AirDefence.Stinger_comm.id,
            AirDefence.Stinger_comm_dsr.id,
        ),
    ),
    (_GEPARD, (AirDefence.Gepard.id,)),
    (_VULCAN, (AirDefence.Vulcan.id,)),
    (_BOX_SPRING, (AirDefence.x_1L13_EWR.id,)),
    (_TALL_RACK, (AirDefence.x_55G6_EWR.id,)),
    (_TALL_KING, (AirDefence.P14_SR.id,)),
    (_FLAT_FACE, (AirDefence.p_19_s_125_sr.id,)),
    (_BIG_BIRD, (AirDefence.S_300PS_64H6E_sr.id,)),
    (_CLAM_SHELL, (AirDefence.S_300PS_40B6MD_sr.id,)),
    (
        _TIN_SHIELD,
        (AirDefence.RLS_19J6.id, AirDefence.S_300PS_40B6MD_sr_19J6.id),
    ),
    (_SNOW_DRIFT, (AirDefence.SA_11_Buk_SR_9S18M1.id,)),
    (_DOG_EAR, (AirDefence.Dog_Ear_radar.id,)),
)

THREAT_REFERENCE: Dict[str, ThreatReference] = {
    unit_id: ref for ref, unit_ids in _SYSTEMS for unit_id in unit_ids
}


def reference_for(unit_type_id: str) -> Optional[ThreatReference]:
    """Catalog entry for a DCS air-defence unit id, or None if uncatalogued."""
    return THREAT_REFERENCE.get(unit_type_id)
