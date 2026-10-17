"""HQ requests (§112) — enemy targets HQ asks the players to take out.

Design: docs/dev/design/retlab-hq-priority-targets-notes.md §9. The order half of
juanjux's High Command, without its prizes (DM call 2026-10-12).

- Drawn after BLUE's auto-planner, from targets it left with no package: the jobs
  nobody else is flying.
- One from each third of difficulty (easy, mid, hard); each stays open 2-5 turns.
- Never a site hidden on blue's map (§3 fog), and difficulty counts only the SAM
  rings blue knows about, so a request never hints at a ring the map hides.
- Achieving one pays nothing. The SITREP says so; that is all.
"""

from __future__ import annotations

import logging
import math
import random
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable, Optional, Sequence

from game.retlab.region_priorities import family_of
from game.theater.player import Player

if TYPE_CHECKING:
    from game import Game
    from game.theater.theatergroundobject import TheaterGroundObject

#: Brady's 2026-10-12 choices: three a turn, one per difficulty third, 2-5 turns.
TIER_NAMES = ("easy", "mid", "hard")
SHORTEST_TURNS = 2
LONGEST_TURNS = 5

#: A mile flown inside a known SAM ring counts as this many miles of route.
RING_MILE_WEIGHT = 3.0

METERS_PER_NM = 1852.0


@dataclass
class HqRequest:
    """One open request. Persisted with the save."""

    tgo_id: uuid.UUID
    name: str
    #: What it is, as the map calls it ("Ammo depot").
    kind: str
    #: The control point it belongs to.
    base: str
    #: 0 easy, 1 mid, 2 hard.
    tier: int
    ordered_on: int
    #: The first turn it is no longer open.
    expires_on: int
    #: The §103 line on why it matters, as it read when drawn.
    why: str = ""
    #: The turn a mission destroyed it; None while open.
    done_on: Optional[int] = None

    @property
    def tier_name(self) -> str:
        return TIER_NAMES[self.tier]

    def turns_left(self, turn: int) -> int:
        return max(0, self.expires_on - turn)


@dataclass
class HqRequests:
    """BLUE's open requests and the turn they were last drawn on."""

    requests: list[HqRequest] = field(default_factory=list)
    drawn_on: Optional[int] = None

    def open(self) -> list[HqRequest]:
        return [r for r in self.requests if r.done_on is None]

    def for_target(self, tgo: Any) -> Optional[HqRequest]:
        tgo_id = getattr(tgo, "id", None)
        return next((r for r in self.open() if r.tgo_id == tgo_id), None)


def enabled(game: Game) -> bool:
    return bool(getattr(game.settings, "hq_requests", False))


def requests_of(game: Game) -> HqRequests:
    """The game's requests; an empty set on a save from before §112."""
    requests = getattr(game, "hq_requests", None)
    if requests is None:
        requests = HqRequests()
        game.hq_requests = requests
    return requests


def _target(game: Game, tgo_id: uuid.UUID) -> Optional[TheaterGroundObject]:
    return next((t for t in game.theater.ground_objects if t.id == tgo_id), None)


def _packaged_targets(game: Game) -> set[int]:
    return {
        id(package.target)
        for package in game.blue.ato.packages
        if getattr(package, "target", None) is not None
    }


def candidates(game: Game) -> list[TheaterGroundObject]:
    """Enemy targets blue can see, alive, with no blue package on them."""
    from game.theater.fogofwar import hidden_from

    packaged = _packaged_targets(game)
    found = []
    for cp in game.theater.controlpoints:
        if cp.captured is not Player.RED:
            continue
        for tgo in cp.ground_objects:
            if family_of(tgo) is None or tgo.category == "motorpool":
                # A motorpool's vehicles are drawn afresh for every mission, so it
                # is never "destroyed".
                continue
            if getattr(tgo, "is_control_point", False) or tgo.is_dead():
                continue
            if id(tgo) in packaged or hidden_from(Player.BLUE, tgo):
                continue
            found.append(tgo)
    return found


@dataclass(frozen=True)
class Ring:
    x: float
    y: float
    radius: float


def known_rings(game: Game) -> list[Ring]:
    """The red threat rings blue's map shows, overview ignored."""
    from game.theater.fogofwar import fog_intact

    rings = []
    with fog_intact():
        for tgo in game.theater.ground_objects:
            if tgo.control_point.captured is not Player.RED or tgo.is_dead():
                continue
            if not tgo.known_for(Player.BLUE):
                continue
            reach = tgo.max_threat_range().meters
            if reach > 0:
                rings.append(Ring(tgo.position.x, tgo.position.y, reach))
    return rings


def blue_bases(game: Game) -> list[tuple[float, float]]:
    """Where blue's aircraft are, as map positions."""
    seen: dict[int, tuple[float, float]] = {}
    for squadron in game.blue.air_wing.iter_squadrons():
        if squadron.owned_aircraft <= 0:
            continue
        cp = squadron.location
        seen[id(cp)] = (cp.position.x, cp.position.y)
    return list(seen.values())


def _inside(ax: float, ay: float, bx: float, by: float, ring: Ring) -> float:
    """Meters of the segment a-b inside the ring."""
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    fx, fy = ax - ring.x, ay - ring.y
    if length_sq == 0:
        return 0.0
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - ring.radius * ring.radius
    disc = b * b - 4 * length_sq * c
    if disc <= 0:
        return 0.0
    root = math.sqrt(disc)
    t1 = max(0.0, (-b - root) / (2 * length_sq))
    t2 = min(1.0, (-b + root) / (2 * length_sq))
    return max(0.0, t2 - t1) * math.sqrt(length_sq)


def difficulty(
    position: tuple[float, float],
    bases: Sequence[tuple[float, float]],
    rings: Iterable[Ring],
) -> float:
    """Route effort in NM: the straight line from the cheapest blue base, each mile
    inside a known ring counted RING_MILE_WEIGHT times. Overlapping rings stack."""
    rings = list(rings)
    tx, ty = position
    best = math.inf
    for bx, by in bases:
        length = math.hypot(tx - bx, ty - by)
        inside = sum(_inside(bx, by, tx, ty, ring) for ring in rings)
        best = min(best, length + (RING_MILE_WEIGHT - 1) * inside)
    return 0.0 if best is math.inf else best / METERS_PER_NM


def thirds(items: Sequence[Any], key: Any) -> list[list[Any]]:
    """Three tiers of near equal size, lowest key first."""
    ranked = sorted(items, key=key)
    total = len(ranked)
    return [ranked[n * total // 3 : (n + 1) * total // 3] for n in range(3)]


def _pick(tier: Sequence[Any], game: Game, rng: random.Random) -> Any:
    """A random target from the more important half of its §103 family, if any."""
    from game.retlab.hq_priorities import HqStandings

    standings = HqStandings(game)
    important = []
    for tgo in tier:
        standing = standings.standing(tgo)
        if standing is not None and standing.of and standing.rank <= standing.of / 2:
            important.append(tgo)
    return rng.choice(important or list(tier))


def _why(tgo: Any, game: Game) -> str:
    from game.retlab.hq_priorities import why_it_matters
    from game.theater.fogofwar import fog_intact

    # Saved on the request: a host's fog reveal at turn end must not bake in.
    with fog_intact():
        return why_it_matters(tgo, game, Player.BLUE) or ""


def refresh(game: Game, rng: Optional[random.Random] = None) -> None:
    """Close what is over and draw a request for each tier left without one.

    Once per turn, after blue's auto-planner: a mid-turn re-plan keeps the turn's
    requests, so they never change under a player who is planning against them.
    """
    requests = requests_of(game)
    if not enabled(game):
        requests.requests.clear()
        requests.drawn_on = None
        return
    if requests.drawn_on == game.turn:
        return
    requests.drawn_on = game.turn
    rng = rng or random.Random()

    kept = []
    expired = set()
    for request in requests.requests:
        if request.done_on is not None:
            continue
        if game.turn >= request.expires_on:
            expired.add(request.tgo_id)
            continue
        tgo = _target(game, request.tgo_id)
        if tgo is None or tgo.is_dead() or tgo.control_point.captured is not Player.RED:
            continue
        kept.append(request)
    requests.requests = kept

    pool = candidates(game)
    if not pool:
        return
    bases = blue_bases(game)
    rings = known_rings(game)
    effort = {
        id(t): difficulty((t.position.x, t.position.y), bases, rings) for t in pool
    }
    busy = {r.tier for r in kept}
    taken = {r.tgo_id for r in kept}
    for tier, members in enumerate(thirds(pool, lambda t: (effort[id(t)], t.name))):
        choices = [t for t in members if t.id not in taken]
        # A request that just ran out comes back only if nothing else is left.
        choices = [t for t in choices if t.id not in expired] or choices
        if tier in busy or not choices:
            continue
        chosen = _pick(choices, game, rng)
        taken.add(chosen.id)
        requests.requests.append(
            HqRequest(
                tgo_id=chosen.id,
                name=chosen.name,
                kind=str(chosen),
                base=chosen.control_point.name,
                tier=tier,
                ordered_on=game.turn,
                expires_on=game.turn + rng.randint(SHORTEST_TURNS, LONGEST_TURNS),
                why=_why(chosen, game),
            )
        )
    requests.requests.sort(key=lambda r: r.tier)


def record_results(game: Game) -> list[str]:
    """Mark the requests the mission just destroyed, one SITREP line each.

    Called after the mission's losses are committed, before the turn passes.
    """
    if not enabled(game):
        return []
    try:
        return _record_results(game)
    except Exception:
        # A fault here must not lose the mission's results.
        logging.exception("Could not check the HQ requests")
        return []


def _record_results(game: Game) -> list[str]:
    lines = []
    for request in requests_of(game).open():
        tgo = _target(game, request.tgo_id)
        if tgo is not None and tgo.is_dead():
            request.done_on = game.turn
            lines.append(f"HQ request done: {request.name} ({request.tier_name})")
    return lines


def brief_line(game: Game, target: Any) -> Optional[str]:
    """The kneeboard BLUF line for a package whose target is an open request."""
    if target is None or not enabled(game):
        return None
    request = requests_of(game).for_target(target)
    if request is None:
        return None
    left = request.turns_left(game.turn)
    return (
        f"HQ REQUEST  {request.tier_name}, {left} turn{'s' if left != 1 else ''} left"
    )


def intel_line(game: Game, tgo: Any) -> Optional[str]:
    """The Target Intel panel row, or None when the target is not a request."""
    if not enabled(game):
        return None
    request = requests_of(game).for_target(tgo)
    if request is None:
        return None
    left = request.turns_left(game.turn)
    return f"Yes ({request.tier_name}), {left} turn{'s' if left != 1 else ''} left"
