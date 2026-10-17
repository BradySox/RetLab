"""AI fills an empty player flight (§113).

A player flight marked "AI fills if no player" gets a late-activated AI copy of
its player seats, the twin. The ``aifill`` plugin checks the player seats a few
minutes in and, if nobody is in any of them, activates the twin at the planned
takeoff time. Design note: docs/dev/design/retlab-ai-fill-notes.md.

This module holds the rule (which flights may carry a twin) and the Lua record.
The twin itself is built in ``game/missiongenerator/aircraft/aitwin.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from dcs.task import ControlledTask, EscortTaskAction

from game.ato.flighttype import FlightType

if TYPE_CHECKING:
    from dcs.unitgroup import FlyingGroup

    from game import Game
    from game.ato import Flight
    from game.missiongenerator.luagenerator import LuaData
    from game.missiongenerator.missiondata import MissionData
    from game.settings import Settings

#: Tasks an AI copy cannot fly the way the players would: cargo and troop moves
#: (CTLD is keyed to the client group), support orbits (a second tanker or AEW&C
#: registration), and the player-only roles (photo recon, rescue, the C-130J EW
#: suite).
NO_AI_FILL_TASKS: frozenset[FlightType] = frozenset(
    {
        FlightType.TRANSPORT,
        FlightType.AIR_ASSAULT,
        FlightType.FERRY,
        FlightType.AEWC,
        FlightType.REFUELING,
        FlightType.RECOVERY,
        FlightType.TARPS,
        FlightType.CSAR,
        FlightType.JAMMING,
    }
)


def offers_ai_fill(flight: Flight) -> bool:
    """Whether the flight may carry an AI twin at all."""
    return (
        flight.client_count > 0
        and flight.cargo is None
        and flight.flight_type not in NO_AI_FILL_TASKS
    )


def ai_fill_wanted(flight: Flight, settings: Settings) -> bool:
    """Whether the mission generator builds a twin for this flight.

    The flight's own box wins; an untouched box follows the campaign setting.
    """
    if not offers_ai_fill(flight):
        return False
    choice = getattr(flight, "ai_fills_if_empty", None)
    if choice is None:
        return settings.ai_fills_empty_player_flights
    return choice


@dataclass(frozen=True)
class AiFillEscort:
    """An escort group's Escort task, to be re-aimed at a twin that launches."""

    group: str
    engagement_max_dist: int
    target_types: tuple[str, ...]
    #: The escort's formation offset (x, y, z), metres.
    position: tuple[float, float, float]
    #: The package's split flag, which ends the task; None if it has none.
    split_flag: Optional[str]


def escort_task_of(group: FlyingGroup[Any]) -> Optional[AiFillEscort]:
    """The Escort task the waypoint generator wrote into the group's route."""
    for point in group.points:
        for task in point.tasks:
            if not isinstance(task, ControlledTask):
                continue
            inner = task.params.get("task", {})
            if inner.get("id") != EscortTaskAction.Id:
                continue
            params = inner.get("params", {})
            pos = params.get("pos", {})
            stop = task.params.get("stopCondition", {}).get("userFlag")
            return AiFillEscort(
                group=str(group.name),
                engagement_max_dist=int(params.get("engagementDistMax", 0)),
                target_types=tuple(params.get("targetTypes", {}).values()),
                position=(
                    float(pos.get("x", 0)),
                    float(pos.get("y", 0)),
                    float(pos.get("z", 0)),
                ),
                split_flag=None if stop is None else str(stop),
            )
    return None


@dataclass(frozen=True)
class AiFillPair:
    """One client group and the AI twin that replaces it if nobody flies it."""

    client_group: str
    twin_group: str
    #: "blue" or "red": whose players are counted.
    coalition: str
    #: Seconds after mission start the twin may launch: its planned takeoff.
    activate_after: int
    #: The coalition message when the twin launches.
    message: str
    #: Seconds after mission start the client group appears. A late-activated
    #: group has no seats to take before then, so the check waits for it.
    client_activation: int = 0
    #: The package's escorts, when the client group is the one they escort.
    escorts: tuple[AiFillEscort, ...] = ()


def populate_ai_fill_lua(
    root: LuaData, game: Game, mission_data: MissionData | None = None
) -> None:
    """Build ``dcsRetribution.aiFill``; nothing when the mission has no twin."""
    pairs = mission_data.ai_fill_pairs if mission_data else []
    if not pairs:
        return
    node = root.add_item("aiFill")
    delay = int(game.settings.ai_fill_check_delay.total_seconds())
    node.add_key_value("checkDelay", str(delay))
    node.add_key_value("announce", "true" if game.settings.ai_fill_announce else "")
    pair_node = node.get_or_create_item("pairs")
    for pair in pairs:
        record = pair_node.add_item()
        record.add_key_value("client", pair.client_group)
        record.add_key_value("twin", pair.twin_group)
        record.add_key_value("coalition", pair.coalition)
        record.add_key_value("activateAfter", str(pair.activate_after))
        record.add_key_value("clientActivation", str(pair.client_activation))
        record.add_key_value("message", pair.message)
        if not pair.escorts:
            continue
        escorts = record.add_item("escorts")
        for escort in pair.escorts:
            item = escorts.add_item()
            item.add_key_value("group", escort.group)
            item.add_key_value("engagementDistMax", str(escort.engagement_max_dist))
            item.add_data_array("targetTypes", list(escort.target_types))
            for axis, value in zip("xyz", escort.position):
                item.add_key_value(axis, str(value))
            if escort.split_flag is not None:
                item.add_key_value("splitFlag", escort.split_flag)
