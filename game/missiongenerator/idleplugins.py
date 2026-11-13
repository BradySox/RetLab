"""Which Lua plugins have nothing to do in a mission, so the mission leaves them out.

A plugin left out is never loaded: no file read at mission start, no event handler,
no scheduler. Every rule here matches a check the script itself makes and then stops
on, so leaving it out changes nothing in the mission. Design note:
docs/dev/design/retlab-idle-plugin-skip-notes.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

#: Plugins whose script stops on its first line unless Python wrote its
#: dcsRetribution table, and that table is written only when the feature has work.
DATA_GATED_PLUGINS: dict[str, str] = {
    "aifill": "aiFill",
    "briefing": "briefing",
    "civtraffic": "civilTraffic",
    "coin": "coin",
    "cruisemissiles": "cruiseMissiles",
    "gpsjamming": "gpsJamming",
    "navalmagazines": "navalMagazines",
    "neutralborder": "neutralBorder",
    "pkgcontrol": "packageControl",
    "radiorecord": "radioRecord",
    "redscramble": "redScramble",
    "vacuum": "vacuum",
    "vietnamops": "VietnamOps",
    "voiceatc": "voiceAtc",
}


@dataclass(frozen=True)
class MissionWork:
    """What the generated mission holds that a plugin could act on."""

    #: The top-level dcsRetribution tables Python wrote.
    data_keys: frozenset[str]
    carriers: int
    #: C-130J-30 flights the mission-systems script would claim.
    ew_c130j_flights: int
    #: CSAR on for either side, or a rescue flight fragged.
    csar_active: bool
    iads_nodes: int
    logistics_flights: int
    jtacs: int


def idle_reason(plugin_id: str, work: MissionWork) -> Optional[str]:
    """Why ``plugin_id`` has nothing to do in this mission, or None to load it."""
    table = DATA_GATED_PLUGINS.get(plugin_id)
    if table is not None:
        if table not in work.data_keys:
            return f"its setting is off or it has nothing to act on (no {table} data)"
        return None
    if plugin_id == "airboss" and work.carriers == 0:
        return "no carrier or LHA in the mission"
    if plugin_id == "c130j" and work.ew_c130j_flights == 0:
        return "no C-130J-30 flies a mission-systems role"
    if plugin_id == "opscsar" and not work.csar_active:
        return "CSAR is off for both sides and no rescue flight is fragged"
    # LotATC reads Skynet's networks and stops without them.
    if plugin_id in ("skynetiads", "lotatc") and work.iads_nodes == 0:
        return "neither side has a SAM or early-warning radar in its network"
    # CTLD gives its menus only to fragged transport pilots, and lases only for JTACs.
    if plugin_id == "ctld" and work.logistics_flights == 0 and work.jtacs == 0:
        return "no Transport or Air Assault flight and no JTAC"
    return None
