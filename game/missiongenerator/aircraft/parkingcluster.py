"""Side-by-side stands for a flight, lead nearest the departure runway end.

pydcs hands a flight the next free stands by name, wherever they sit. At Spangdahlem in
test 64 an AI four-ship got stands 48-51, lead south of the main junction and wingmen
200-270 m north-east of it; the wingmen drove the wrong way to fall in behind the lead,
met it nose to nose and all four froze for the mission, trapping two flights behind them.
Notes: features doc §8, "Flight parking clusters".
"""

from __future__ import annotations

import heapq
import math
from typing import Any, Optional, Sequence

from dcs.terrain.terrain import Airport, ParkingSlot

#: A cluster wider than this is no better than pydcs's own pick. Four 15 m shelters at
#: Spangdahlem sit within ~110 m; a row of 18 m stands within ~70 m.
MAX_CLUSTER_SPREAD_M = 150.0

#: pydcs carries no runway length or threshold position, so the threshold is this far
#: from the field's reference point along the runway heading (as in airfieldclearance).
RUNWAY_HALF_LENGTH_M = 1600.0


def _distance(a: ParkingSlot, b: ParkingSlot) -> float:
    return math.hypot(a.position.x - b.position.x, a.position.y - b.position.y)


def _spread(slots: Sequence[ParkingSlot]) -> float:
    return max(
        (_distance(a, b) for i, a in enumerate(slots) for b in slots[i + 1 :]),
        default=0.0,
    )


def runway_thresholds(
    airport: Airport, departure_heading: Optional[float]
) -> list[tuple[float, float]]:
    """Where a departure lines up: the threshold behind the takeoff heading.

    With no known departure heading, both ends of every runway.
    """
    headings: list[float] = []
    if departure_heading is not None:
        headings = [departure_heading]
    else:
        for runway in getattr(airport, "runways", []) or []:
            headings += [runway.main.heading, runway.opposite.heading]
    points = []
    for heading in headings:
        rad = math.radians(heading)
        points.append(
            (
                airport.position.x - RUNWAY_HALF_LENGTH_M * math.cos(rad),
                airport.position.y - RUNWAY_HALF_LENGTH_M * math.sin(rad),
            )
        )
    return points


def _best_cluster(
    pool: list[ParkingSlot], count: int
) -> Optional[tuple[float, list[ParkingSlot]]]:
    best: Optional[tuple[float, int, list[ParkingSlot]]] = None
    for index, anchor in enumerate(pool):
        neighbours = heapq.nsmallest(
            count - 1,
            ((_distance(anchor, s), i) for i, s in enumerate(pool) if i != index),
        )
        cluster = [anchor] + [pool[i] for _, i in neighbours]
        key = (_spread(cluster), index)
        if best is None or key < (best[0], best[1]):
            best = (key[0], index, cluster)
    if best is None:
        return None
    return best[0], best[2]


def cluster_parking_slots(
    airport: Airport,
    aircraft_type: Any,
    count: int,
    departure_heading: Optional[float] = None,
) -> Optional[list[ParkingSlot]]:
    """The stands for a flight of ``count``, lead first, or None for pydcs's pick.

    Candidates are pydcs's own free list for the type (fit, taken and blocked stands
    already filtered), tried tier by tier in its (helicopter, width) order so a fighter
    does not take a transport's stand while a smaller one fits. None for a single ship,
    too few stands, or no cluster within ``MAX_CLUSTER_SPREAD_M``.
    """
    if count < 2:
        return None
    free: list[ParkingSlot] = list(airport.free_parking_slots(aircraft_type))
    if len(free) < count:
        return None

    tiers: list[tuple[Any, Any]] = []
    for slot in free:
        tier = (slot.helicopter, slot.width)
        if tier not in tiers:
            tiers.append(tier)
    chosen: Optional[list[ParkingSlot]] = None
    for depth in range(1, len(tiers) + 1):
        allowed = set(tiers[:depth])
        pool = [s for s in free if (s.helicopter, s.width) in allowed]
        if len(pool) < count:
            continue
        found = _best_cluster(pool, count)
        if found is not None and found[0] <= MAX_CLUSTER_SPREAD_M:
            chosen = found[1]
            break
    if chosen is None:
        return None

    thresholds = runway_thresholds(airport, departure_heading)
    if not thresholds:
        return chosen

    def to_runway(slot: ParkingSlot) -> float:
        return min(
            math.hypot(slot.position.x - x, slot.position.y - y) for x, y in thresholds
        )

    # Python's sort is stable, so equal distances keep the cluster's own order.
    return sorted(chosen, key=to_runway)
