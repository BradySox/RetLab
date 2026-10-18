"""Heatblur airframes spawn at a period build quality (features doc §43).

Heatblur's F-4E and A-6E carry "Aircraft Condition" (``Quality``) and "Aircraft Wear
and Tear" (``Wear``). The module default of 100 condition is "showroom/prototype
grade" on Heatblur's own scale (F-4E manual, Mission Editor chapter); 90 is a
standard service jet. A value the player set in the payload tab, or a saved
default, always wins. DCS applies both only to player aircraft.
"""

from __future__ import annotations

from datetime import date
from typing import Any

QUALITY_PROPERTY = "Quality"
WEAR_PROPERTY = "Wear"

#: Heatblur's "standard western build".
SERVICE_CONDITION = 90
#: Before 1980: looser builds and wartime maintenance, between Heatblur's 75
#: ("slightly below standard") and 50.
EARLY_CONDITION = 75
EARLY_ERA_ENDS = 1980


def has_condition_properties(dcs_unit_type: Any) -> bool:
    properties = getattr(dcs_unit_type, "properties", None) or {}
    return QUALITY_PROPERTY in properties and WEAR_PROPERTY in properties


def baseline_condition(when: date) -> int:
    return EARLY_CONDITION if when.year < EARLY_ERA_ENDS else SERVICE_CONDITION


def condition_defaults(dcs_unit_type: Any, when: date) -> dict[str, int]:
    """The values an untouched condition knob spawns with; empty for other jets.

    The generator fills only keys the player left unset, and the payload tab shows
    these in place of the module defaults so the box reads what will fly.
    """
    if not has_condition_properties(dcs_unit_type):
        return {}
    return {QUALITY_PROPERTY: baseline_condition(when)}
