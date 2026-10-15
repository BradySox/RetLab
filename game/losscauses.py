"""What killed each side's losses last turn, for the outside AI (features doc §109).

The base plugin records the killer DCS names in ``S_EVENT_KILL``
(``kill_causes`` in state.json). This sorts each of those kills by what did it:
an aircraft, a SAM, AAA, a ship or ground fire. A loss with no kill event (a
crash, a collision, fuel) has no entry, so the causes can add up to fewer than
the losses. The idea is from Hussar2477/dcs-retribution's ``llm-ai-opponent``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, TYPE_CHECKING, cast

from game.data.units import UnitClass
from game.theater.player import Player

if TYPE_CHECKING:
    from game.unitmap import UnitMap

AIRCRAFT = "aircraft"
SAM = "sam"
AAA = "aaa"
SHIP = "ship"
GROUND = "ground"
OWN_SIDE = "own_side"
UNKNOWN = "unknown"

#: The three kinds of loss ``LastTurnView`` already counts.
KIND_AIRCRAFT = "aircraft"
KIND_FRONT_LINE = "front_line"
KIND_SITES = "sites"

_AAA_CLASSES = {UnitClass.AAA, UnitClass.AAA_RADAR}
_SAM_CLASSES = {
    UnitClass.LAUNCHER,
    UnitClass.TELAR,
    UnitClass.SHORAD,
    UnitClass.MANPAD,
    UnitClass.SEARCH_RADAR,
    UnitClass.TRACK_RADAR,
    UnitClass.SEARCH_TRACK_RADAR,
    UnitClass.SPECIALIZED_RADAR,
}
_SHIP_CLASSES = {
    UnitClass.AIRCRAFT_CARRIER,
    UnitClass.HELICOPTER_CARRIER,
    UnitClass.CRUISER,
    UnitClass.DESTROYER,
    UnitClass.FRIGATE,
    UnitClass.BOAT,
    UnitClass.LANDING_SHIP,
    UnitClass.SUBMARINE,
}

#: How many killer types and weapons are kept per side.
TOP_N = 5


@dataclass(frozen=True)
class KillCause:
    """One ``S_EVENT_KILL`` as the mission reported it."""

    target: str
    killer: str
    killer_type: Optional[str] = None
    weapon: Optional[str] = None

    @staticmethod
    def parse(raw: Any) -> tuple["KillCause", ...]:
        # A Lua JSON encoder writes an empty table as [] or {}; old state files
        # have no key at all.
        if not isinstance(raw, list):
            return ()
        causes = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            target, killer = entry.get("target"), entry.get("killer")
            if not isinstance(target, str) or not isinstance(killer, str):
                continue
            killer_type, weapon = entry.get("killer_type"), entry.get("weapon")
            causes.append(
                KillCause(
                    target,
                    killer,
                    killer_type if isinstance(killer_type, str) else None,
                    weapon if isinstance(weapon, str) and weapon else None,
                )
            )
        return tuple(causes)


@dataclass
class SideLossCauses:
    """One side's losses with a recorded killer, by kind of loss and by cause."""

    #: ``{"aircraft" | "front_line" | "sites": {cause: count}}``.
    by_cause: dict[str, dict[str, int]] = field(default_factory=dict)
    #: What shot its aircraft down: the killers' type names, most first.
    aircraft_killers: dict[str, int] = field(default_factory=dict)
    #: And with what.
    aircraft_weapons: dict[str, int] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.by_cause


def _owner(
    unit_map: "UnitMap", name: str, owners_before: Optional[dict[int, Player]] = None
) -> Optional[tuple[Player, str, Any]]:
    """(side, kind of loss, unit class or None) for a unit name, or None."""

    def side_of(control_point: Any) -> Player:
        # A base captured this mission has changed hands by the time this is read.
        if owners_before and id(control_point) in owners_before:
            return owners_before[id(control_point)]
        return cast(Player, control_point.captured)

    flying = unit_map.flight(name)
    if flying is not None:
        return side_of(flying.flight.departure), KIND_AIRCRAFT, None
    front = unit_map.front_line_unit(name)
    if front is None:
        front = unit_map.motorpool_unit(name)
    if front is not None:
        return side_of(front.origin), KIND_FRONT_LINE, front.unit_type.unit_class
    convoy = unit_map.convoy_unit(name)
    if convoy is not None:
        return (
            convoy.convoy.player_owned,
            KIND_FRONT_LINE,
            convoy.unit_type.unit_class,
        )
    theater = unit_map.theater_units(name)
    if theater is not None:
        unit = theater.theater_unit
        unit_class = unit.unit_type.unit_class if unit.unit_type is not None else None
        return side_of(unit.ground_object.control_point), KIND_SITES, unit_class
    return None


def _cause(kind: str, unit_class: Any) -> str:
    if kind == KIND_AIRCRAFT:
        return AIRCRAFT
    if unit_class in _SHIP_CLASSES:
        return SHIP
    if unit_class in _AAA_CLASSES:
        return AAA
    if unit_class in _SAM_CLASSES:
        return SAM
    return GROUND


def _top(counter: Counter[str]) -> dict[str, int]:
    return dict(counter.most_common(TOP_N))


def tally(
    kill_causes: Iterable[KillCause],
    unit_map: "UnitMap",
    owners_before: Optional[dict[int, Player]] = None,
) -> dict[str, SideLossCauses]:
    """Losses by cause for each side, keyed ``"blue"`` and ``"red"``.

    ``owners_before`` maps ``id(control point)`` to who held it during the mission,
    for the bases captured in it: the sitrep is written after captures commit."""
    by_cause: dict[str, dict[str, Counter[str]]] = {"blue": {}, "red": {}}
    killers: dict[str, Counter[str]] = {"blue": Counter(), "red": Counter()}
    weapons: dict[str, Counter[str]] = {"blue": Counter(), "red": Counter()}
    seen: set[str] = set()
    for kill in kill_causes:
        if kill.target in seen:
            continue
        victim = _owner(unit_map, kill.target, owners_before)
        if victim is None:
            continue
        seen.add(kill.target)
        side, kind, _ = victim
        if side.is_neutral:
            continue
        key = "blue" if side.is_blue else "red"
        killer = _owner(unit_map, kill.killer, owners_before)
        if killer is None:
            cause = UNKNOWN
        elif killer[0] == side:
            cause = OWN_SIDE
        else:
            cause = _cause(killer[1], killer[2])
        by_cause[key].setdefault(kind, Counter())[cause] += 1
        if kind == KIND_AIRCRAFT:
            if kill.killer_type:
                killers[key][kill.killer_type] += 1
            if kill.weapon:
                weapons[key][kill.weapon] += 1
    return {
        key: SideLossCauses(
            by_cause={kind: dict(counts) for kind, counts in by_cause[key].items()},
            aircraft_killers=_top(killers[key]),
            aircraft_weapons=_top(weapons[key]),
        )
        for key in ("blue", "red")
    }
