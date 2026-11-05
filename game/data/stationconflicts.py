"""Stations an aircraft cannot load at the same time.

DCS declares these per store in the module's own Lua (``forbidden``/``required``),
which pydcs does not export, so a fit that breaks one reaches the mission and DCS
drops a store at spawn (test 68: F-4E Mk-83 TERs inboard beside AIM-9s lost the
TERs). The rules are copied from the module files; see
docs/dev/retlab-features.md §8, Loadouts and module data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping, MutableMapping, Optional, Protocol, TypeVar


class _HasClsid(Protocol):
    @property
    def clsid(self) -> str: ...


_Store = TypeVar("_Store", bound=_HasClsid)


@dataclass(frozen=True)
class SharedPylon:
    """A pylon whose listed stores take the rails beside it off."""

    pylon: int
    rails: tuple[int, ...]
    #: Stores on ``pylon`` the module forbids beside a loaded rail. A store not
    #: listed (an SWA adapter load, a mod's store) leaves the rails alone.
    blocking: frozenset[str]

    def blocks_rails(self, clsid: Optional[str]) -> bool:
        return clsid in self.blocking


# Heatblur F-4E, CoreMods/aircraft/F-4E/Entry/F-4E.lua create_inner_wing_loadout:
# every inboard store tagged Aim9Restrict, with its add_gp_bomb and add_maverick
# loops expanded. <CLEAN> is one: no inboard pylon, no shoulder rails.
_F4E_INBOARD_BLOCKING = frozenset(
    {
        "{CBU-87}",
        "{HB_F4E_CBU-87_2x}",
        "{CBU-52B}",
        "{HB_F4E_CBU-52B_2x}",
        "{HB_F4E_CBU-7A_3x}",
        "{HB_F4E_CBU-7A_2x}",
        "{HB_F4E_CBU-7A_1x_Alt}",
        "{HB_F4E_CBU-7A_1x}",
        "{HB_F4E_CBU-38A_3x}",
        "{HB_F4E_CBU-38A_2x}",
        "{HB_F4E_CBU-38A_1x_Alt}",
        "{HB_F4E_CBU-38A_1x}",
        "{HB_F4E_BLU-107B_3x}",
        "{HB_F4E_MK-83_3x}",
        "{HB_F4E_M117_3x}",
        "{HB_F4E_BL755_TER_3x}",
        "{HB_F4E_BL755_TER_2x_opposed}",
        "{HB_F4E_BL755_TER_1x_SingleRight}",
        "{HB_F4E_SAMP250LD_TER_3x}",
        "{HB_F4E_SAMP250LD_TER_2x_opposed}",
        "{HB_F4E_SAMP250LD_TER_1x_SingleRight}",
        "{HB_F4E_SAMP250HD_TER_3x}",
        "{HB_F4E_SAMP250HD_TER_2x_opposed}",
        "{HB_F4E_SAMP250HD_TER_1x_SingleRight}",
        "{Mk_84AIR_GP}",
        "{34759BBC-AF1E-4AEE-A581-498FF7A6EBCE}",
        "{51F9AAE5-964F-4D21-83FB-502E3BFE5F8A}",
        "{DB769D48-67D7-42ED-A2BE-108D566C8B1E}",
        "{HB_F4E_GBU-12_2x}",
        "{BDU_45LG}",
        "{HB_F4E_BDU_45LGB_2x}",
        "{GD_F100_BOLT117}",
        "{HB_F4E_BOLT-117_2x}",
        "{HB_F4E_AGM-65G_LAU117}",
        "{LAU_34_AGM_45A}",
        "{LAU_34_AGM_45B}",
        "{C40A1E3A-DD05-40D9-85A4-217729E37FAE}",
        "{AGM_62_I}",
        "{GBU_8_B}",
        "{AGM_12A}",
        "{AGM_12B}",
        "{AGM_12C}",
        "{HB_F4E_LAU-68_MK5_1x}",
        "{HB_F4E_LAU-68_MK1_1x}",
        "{HB_F4E_LAU-68_WP156_1x}",
        "{HB_F4E_LAU-68_MK5_3x}",
        "{HB_F4E_LAU-68_MK1_3x}",
        "{HB_F4E_LAU-68_WP156_3x}",
        "{HB_F4E_LAU-3_WP156_1x}",
        "{HB_F4E_LAU-3_MK1_1x}",
        "{HB_F4E_LAU-3_MK5_1x}",
        "{HB_F4E_LAU-3_WP156_3x}",
        "{HB_F4E_LAU-3_MK1_3x}",
        "{HB_F4E_LAU-3_MK5_3x}",
        "{HB_F4E_LAU-10_ZUNI_3x}",
        "{HB_F4E_LAU-10_ZUNI_2x_Opposed}",
        "{HB_F4E_LAU-10_ZUNI_1x}",
        "{F3EFE0AB-E91A-42D8-9CA2-B63C91ED570A}",
        "{LAU3_FFAR_WP156}",
        "{LAU3_FFAR_MK1HE}",
        "{LAU3_FFAR_MK5HEAT}",
        "{6D21ECEA-F85B-4E8D-9D51-31DC9B8AA4EF}",
        "<CLEAN>",
        "{HB_F4E_MK-83_2x_Left}",
        "{HB_F4E_M117_2x_Left}",
        "{HB_F4E_LAU-68_MK5_2x_Left}",
        "{HB_F4E_LAU-68_MK1_2x_Left}",
        "{HB_F4E_LAU-68_WP156_2x_Left}",
        "{HB_F4E_LAU-3_MK5_2x_Left}",
        "{HB_F4E_LAU-3_MK1_2x_Left}",
        "{HB_F4E_LAU-3_WP156_2x_Left}",
        "{HB_F4E_LAU-10_ZUNI_2x_Left}",
        "{HB_F4E_MK-83_2x_Right}",
        "{HB_F4E_M117_2x_Right}",
        "{HB_F4E_LAU-68_MK5_2x_Right}",
        "{HB_F4E_LAU-68_MK1_2x_Right}",
        "{HB_F4E_LAU-68_WP156_2x_Right}",
        "{HB_F4E_LAU-3_MK5_2x_Right}",
        "{HB_F4E_LAU-3_MK1_2x_Right}",
        "{HB_F4E_LAU-3_WP156_2x_Right}",
        "{HB_F4E_LAU-10_ZUNI_2x_Right}",
        "{HB_F4E_MK-81_3x}",
        "{HB_F4E_MK-81_2x}",
        "{HB_F4E_MK-82_3x}",
        "{HB_F4E_MK-82_2x}",
        "{HB_F4E_MK-82_Snakeye_3x}",
        "{HB_F4E_MK-82_Snakeye_2x}",
        "{HB_F4E_ROCKEYE_3x}",
        "{HB_F4E_ROCKEYE_2x}",
        "{HB_F4E_MK-82AIR_3x}",
        "{HB_F4E_MK-82AIR_2x}",
        "{HB_F4E_BDU-50LD_3x}",
        "{HB_F4E_BDU-50LD_2x}",
        "{HB_F4E_BDU-50HD_3x}",
        "{HB_F4E_BDU-50HD_2x}",
        "{HB_F4E_BDU-33_3x}",
        "{HB_F4E_BDU-33_2x}",
        "{HB_F4E_AGM-65A_LAU117}",
        "{HB_F4EAGM-65A_LAU88_3x_Left}",
        "{HB_F4EAGM-65A_LAU88_3x_Right}",
        "{HB_F4EAGM-65A_LAU88_2x_Left}",
        "{HB_F4EAGM-65A_LAU88_2x_Right}",
        "{HB_F4E_AGM-65B_LAU117}",
        "{HB_F4EAGM-65B_LAU88_3x_Left}",
        "{HB_F4EAGM-65B_LAU88_3x_Right}",
        "{HB_F4EAGM-65B_LAU88_2x_Left}",
        "{HB_F4EAGM-65B_LAU88_2x_Right}",
        "{HB_F4E_AGM-65D_LAU117}",
        "{HB_F4EAGM-65D_LAU88_3x_Left}",
        "{HB_F4EAGM-65D_LAU88_3x_Right}",
        "{HB_F4EAGM-65D_LAU88_2x_Left}",
        "{HB_F4EAGM-65D_LAU88_2x_Right}",
    }
)
_F4E = (
    SharedPylon(3, (2, 4), _F4E_INBOARD_BLOCKING),
    SharedPylon(11, (10, 12), _F4E_INBOARD_BLOCKING),
)

SHARED_PYLONS: dict[str, tuple[SharedPylon, ...]] = {
    "F-4E-45MC": _F4E,
}


def _rail_loaded(clsid: Optional[str]) -> bool:
    return bool(clsid) and clsid != "<CLEAN>"


def _clsid(store: Optional[_HasClsid]) -> Optional[str]:
    return None if store is None else store.clsid


def blocked_by(
    aircraft_id: str, pylons: Mapping[int, Optional[_HasClsid]], changed: int
) -> list[int]:
    """Stations that must be emptied for the store now on ``changed`` to fit.

    The last pick wins, as in the DCS Mission Editor: a blocking store on the
    shared pylon clears its rails, and a store on a rail clears the shared pylon.
    """
    cleared: list[int] = []
    for shared in SHARED_PYLONS.get(aircraft_id, ()):
        if changed == shared.pylon:
            if shared.blocks_rails(_clsid(pylons.get(changed))):
                cleared.extend(
                    rail
                    for rail in shared.rails
                    if _rail_loaded(_clsid(pylons.get(rail)))
                )
        elif changed in shared.rails:
            if _rail_loaded(_clsid(pylons.get(changed))) and shared.blocks_rails(
                _clsid(pylons.get(shared.pylon))
            ):
                cleared.append(shared.pylon)
    return cleared


def conflicting_rails(
    aircraft_id: str, pylons: Mapping[int, Optional[_HasClsid]]
) -> list[int]:
    """Rails loaded beside a shared pylon whose store takes them off."""
    rails: list[int] = []
    for shared in SHARED_PYLONS.get(aircraft_id, ()):
        if shared.blocks_rails(_clsid(pylons.get(shared.pylon))):
            rails.extend(
                rail for rail in shared.rails if _rail_loaded(_clsid(pylons.get(rail)))
            )
    return rails


def drop_conflicting_rails(
    aircraft_id: str, pylons: MutableMapping[int, Optional[_Store]], flight_name: str
) -> list[int]:
    """Empty the rails DCS would keep at the cost of the shared pylon's store.

    DCS resolves the clash by dropping the pylon store (a strike's bombs); the
    rail missiles are the smaller loss.
    """
    rails = conflicting_rails(aircraft_id, pylons)
    for rail in rails:
        logging.warning(
            f"{flight_name}: station {rail} emptied; {aircraft_id} cannot carry it "
            "beside the store on the pylon next to it"
        )
        del pylons[rail]
    return rails
