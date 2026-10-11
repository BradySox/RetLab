"""GAU-8 ammunition, as DCS's ``CoreMods/aircraft/A-10/A-10A.lua`` lists it.

The A-10C and A-10C II inherit the list. DCS writes the one-based index into the
unit's ``payload.ammo_type``, not into AddPropAircraft or the IFFCC settings.

Ported from juanjux/dcs-escalation (LGPL-3.0).
"""

GAU8_AIRCRAFT = frozenset({"A-10A", "A-10C", "A-10C_2"})
GAU8_DEFAULT_AMMUNITION = 1
GAU8_AMMUNITION = {
    1: "CM Combat Mix",
    2: "HEI High Explosive Incendiary",
    3: "TP Target Practice",
}
