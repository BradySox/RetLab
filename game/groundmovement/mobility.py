"""Which ground units can drive themselves, need a tow, or never move.

The ground-movement foundation (features doc, ground movement port plan, stage 1).
Data lives per unit as ``ground_mobility`` in resources/units/ground_units/*.yaml.
Adapted from juanjux/dcs-escalation game/groundmovement/mobility.py (LGPL-3.0).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, TYPE_CHECKING

from game.data.units import UnitClass

if TYPE_CHECKING:
    from game.dcs.groundunittype import GroundUnitType


class MobilityMode(Enum):
    #: Not reviewed: never moved by ground movement.
    UNKNOWN = "unknown"
    FIXED = "fixed"
    SELF_PROPELLED = "self_propelled"
    #: Needs a truck that ``can_tow``.
    TOWED = "towed"


@dataclass(frozen=True)
class GroundMobility:
    mode: MobilityMode = MobilityMode.UNKNOWN
    can_tow: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.mode, MobilityMode) or type(self.can_tow) is not bool:
            raise ValueError("Invalid ground mobility data")
        if self.can_tow and self.mode is not MobilityMode.SELF_PROPELLED:
            raise ValueError("A tractor must be self propelled")

    @classmethod
    def from_data(cls, data: Any) -> GroundMobility:
        if data is None:
            return cls()
        if not isinstance(data, dict) or set(data) - {"mode", "can_tow"}:
            raise ValueError("Invalid ground mobility fields")
        return cls(
            MobilityMode(data.get("mode", "unknown")), data.get("can_tow", False)
        )


def movement_mobility(unit: GroundUnitType) -> GroundMobility:
    """Infantry and MANPADS walk; they never count as tractors.

    A unit marked ``mobile: false`` (it cannot drive in DCS, §49) is fixed whatever
    its ``ground_mobility`` says: one undrivable member pins a whole group.
    """
    if not unit.mobile:
        return GroundMobility(MobilityMode.FIXED)
    if unit.unit_class in (UnitClass.INFANTRY, UnitClass.MANPAD):
        return GroundMobility(MobilityMode.SELF_PROPELLED)
    return unit.ground_mobility
