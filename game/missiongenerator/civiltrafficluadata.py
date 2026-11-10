"""Civil traffic -> Lua bridge (``dcsRetribution.civilTraffic``).

Serializes the schedule ``CivilianTrafficGenerator`` built; the ``civtraffic`` plugin
switches queued flights on to hold each layer at its target. Values are Lua strings
(the ``LuaItem`` contract). Exit points are terrain XY: pydcs ``Point.x``/``.y`` is
DCS ``x``/``z``. Emits nothing when the setting is off or nothing was spawned.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .luagenerator import LuaData
    from .missiondata import MissionData


def populate_civil_traffic_lua(root: LuaData, mission_data: MissionData) -> None:
    plan = mission_data.civil_traffic
    if plan is None or not plan.flights:
        return
    node = root.add_item("civilTraffic")
    targets = node.add_item("targets")
    for layer, target in plan.targets.items():
        targets.add_key_value(layer, str(target))
    flights = node.add_item("flights")
    for flight in plan.flights:
        item = flights.add_item()
        item.add_key_value("group", flight.group)
        item.add_key_value("layer", flight.layer)
        item.add_key_value("queued", "true" if flight.queued else "")
        item.add_key_value("maxAge", str(flight.max_age_s))
        if flight.exit_point is not None:
            item.add_key_value("exitX", str(round(flight.exit_point[0])))
            item.add_key_value("exitZ", str(round(flight.exit_point[1])))
        if flight.field is not None:
            item.add_key_value("field", flight.field)
