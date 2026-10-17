import random
import uuid
from typing import Any, Optional, cast

from game.retlab import hq_requests
from game.retlab.hq_requests import (
    HqRequests,
    Ring,
    brief_line,
    difficulty,
    intel_line,
    record_results,
    refresh,
    thirds,
)
from game.theater.player import Player

NM = 1852.0


class FakeSettings:
    def __init__(self, on: bool = True) -> None:
        self.hq_requests = on
        self.hq_priority_targets = False
        self.c2_decapitation_effects = False
        self.enemy_income_multiplier = 1.0


class FakeUnit:
    def __init__(self) -> None:
        self.alive = True


class FakePosition:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class FakeDistance:
    def __init__(self, meters: float) -> None:
        self.meters = meters


class FakeControlPoint:
    def __init__(
        self, name: str, captured: Player = Player.RED, x: float = 0.0
    ) -> None:
        self.name = name
        self.captured = captured
        self.position = FakePosition(x, 0.0)
        self.ground_objects: list[Any] = []
        self.coalition = object()
        self.active_ammo_depots_count = 0


class FakeTgo:
    def __init__(
        self,
        cp: FakeControlPoint,
        name: str,
        x_nm: float,
        category: str = "factory",
        buildings: int = 1,
        hidden: bool = False,
        known: bool = True,
        reach_nm: float = 0.0,
    ) -> None:
        self.id = uuid.uuid4()
        self.name = name
        self.control_point = cp
        self.category = category
        self.position = FakePosition(x_nm * NM, 0.0)
        self.statics = [FakeUnit() for _ in range(buildings)]
        self.value = 10
        self.hidden = hidden
        self.known = known
        self.reach = reach_nm * NM
        self.coalition = cp.coalition
        cp.ground_objects.append(self)

    def __str__(self) -> str:
        return "Factory"

    def is_dead(self) -> bool:
        return not any(unit.alive for unit in self.statics)

    def kill(self) -> None:
        for unit in self.statics:
            unit.alive = False

    def alive_unit_count(self) -> int:
        return sum(1 for unit in self.statics if unit.alive)

    def hidden_on_player_map(self, viewer: Player) -> bool:
        return self.hidden

    def known_for(self, viewer: Player) -> bool:
        return self.known

    def max_threat_range(self) -> FakeDistance:
        return FakeDistance(self.reach)


class FakePackage:
    def __init__(self, target: Any) -> None:
        self.target = target


class FakeSquadron:
    def __init__(self, location: FakeControlPoint) -> None:
        self.location = location
        self.owned_aircraft = 4


class FakeAirWing:
    def __init__(self, squadrons: list[FakeSquadron]) -> None:
        self.squadrons = squadrons

    def iter_squadrons(self) -> list[FakeSquadron]:
        return self.squadrons


class FakeAto:
    def __init__(self) -> None:
        self.packages: list[FakePackage] = []


class FakeCoalition:
    def __init__(self, squadrons: list[FakeSquadron]) -> None:
        self.ato = FakeAto()
        self.air_wing = FakeAirWing(squadrons)


class FakeTheater:
    def __init__(self, *cps: FakeControlPoint) -> None:
        self.controlpoints = list(cps)

    @property
    def ground_objects(self) -> list[Any]:
        return [tgo for cp in self.controlpoints for tgo in cp.ground_objects]


class FakeGame:
    def __init__(self, settings: Optional[FakeSettings] = None) -> None:
        self.settings = settings or FakeSettings()
        self.home = FakeControlPoint("Home", Player.BLUE)
        self.enemy = FakeControlPoint("Enemy")
        self.theater = FakeTheater(self.home, self.enemy)
        self.blue = FakeCoalition([FakeSquadron(self.home)])
        self.turn = 3
        self.hq_requests = HqRequests()


def _game_with_targets(count: int = 9) -> tuple[FakeGame, list[FakeTgo]]:
    game = FakeGame()
    targets = [
        FakeTgo(game.enemy, f"Target {n}", x_nm=10.0 * (n + 1)) for n in range(count)
    ]
    return game, targets


def _refresh(game: FakeGame, seed: int = 1) -> None:
    refresh(cast(Any, game), random.Random(seed))


def _names(game: FakeGame) -> list[str]:
    return [r.name for r in game.hq_requests.open()]


def test_three_requests_one_per_difficulty_third() -> None:
    game, _ = _game_with_targets()
    _refresh(game)
    tiers = {r.tier: r.name for r in game.hq_requests.open()}
    assert set(tiers) == {0, 1, 2}
    assert tiers[0] in {"Target 0", "Target 1", "Target 2"}
    assert tiers[1] in {"Target 3", "Target 4", "Target 5"}
    assert tiers[2] in {"Target 6", "Target 7", "Target 8"}


def test_lifetime_is_two_to_five_turns() -> None:
    for seed in range(20):
        game, _ = _game_with_targets()
        _refresh(game, seed)
        for request in game.hq_requests.open():
            assert 2 <= request.expires_on - request.ordered_on <= 5


def test_a_target_the_auto_planner_took_is_never_requested() -> None:
    game, targets = _game_with_targets(3)
    game.blue.ato.packages.append(FakePackage(targets[1]))
    _refresh(game)
    assert "Target 1" not in _names(game)


def test_a_site_hidden_on_the_map_is_never_requested() -> None:
    game = FakeGame()
    FakeTgo(game.enemy, "Hidden", x_nm=10.0, hidden=True)
    _refresh(game)
    assert _names(game) == []


def test_the_saved_why_line_ignores_the_fog_reveal(monkeypatch: Any) -> None:
    from game.retlab import hq_priorities
    from game.theater import fogofwar

    seen: list[bool] = []

    def why(tgo: Any, game: Any, viewer: Player) -> str:
        seen.append(fogofwar.fog_revealed())
        return "why"

    monkeypatch.setattr(hq_priorities, "why_it_matters", why)
    game, _ = _game_with_targets()
    fogofwar.set_fog_revealed(True)
    try:
        _refresh(game)
    finally:
        fogofwar.set_fog_revealed(False)
    assert seen and not any(seen)


def test_motorpools_and_friendly_targets_are_never_requested() -> None:
    game = FakeGame()
    FakeTgo(game.enemy, "Pool", x_nm=10.0, category="motorpool")
    FakeTgo(game.home, "Ours", x_nm=10.0)
    _refresh(game)
    assert _names(game) == []


def test_drawn_once_a_turn() -> None:
    game, targets = _game_with_targets()
    _refresh(game, 1)
    first = _names(game)
    for target in targets:
        if target.name in first:
            target.kill()
    _refresh(game, 2)
    assert _names(game) == first


def test_a_destroyed_request_is_reported_and_replaced_next_turn() -> None:
    game, targets = _game_with_targets()
    _refresh(game)
    easy = game.hq_requests.open()[0]
    next(t for t in targets if t.id == easy.tgo_id).kill()
    lines = record_results(cast(Any, game))
    assert lines == [f"HQ request done: {easy.name} (easy)"]
    game.turn += 1
    _refresh(game)
    open_now = game.hq_requests.open()
    assert len(open_now) == 3
    assert easy.name not in [r.name for r in open_now]


def test_an_expired_request_is_replaced_from_the_same_tier() -> None:
    game, _ = _game_with_targets()
    _refresh(game)
    hard = game.hq_requests.open()[2]
    game.turn = hard.expires_on
    _refresh(game)
    replacement = next(r for r in game.hq_requests.open() if r.tier == 2)
    assert replacement.ordered_on == game.turn
    assert replacement.name != hard.name


def test_off_clears_the_requests() -> None:
    game, _ = _game_with_targets()
    _refresh(game)
    game.settings.hq_requests = False
    game.turn += 1
    _refresh(game)
    assert game.hq_requests.requests == []


def test_a_known_ring_makes_a_target_harder() -> None:
    base = [(0.0, 0.0)]
    clear = difficulty((30 * NM, 0.0), base, [])
    ringed = difficulty((30 * NM, 0.0), base, [Ring(30 * NM, 0.0, 10 * NM)])
    assert clear == 30.0
    assert ringed == 30.0 + 2 * 10.0


def test_an_unknown_ring_does_not_count() -> None:
    game = FakeGame()
    FakeTgo(game.enemy, "Unknown SAM", x_nm=50.0, known=False, reach_nm=20.0)
    FakeTgo(game.enemy, "Known SAM", x_nm=90.0, reach_nm=10.0)
    rings = hq_requests.known_rings(cast(Any, game))
    assert [ring.radius for ring in rings] == [10 * NM]


def test_thirds_split_evenly() -> None:
    assert thirds(list(range(9)), lambda n: n) == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert thirds([1, 0], lambda n: n) == [[], [0], [1]]


def test_the_kneeboard_and_panel_name_an_open_request() -> None:
    game, targets = _game_with_targets()
    _refresh(game)
    request = game.hq_requests.open()[1]
    target = next(t for t in targets if t.id == request.tgo_id)
    left = request.expires_on - game.turn
    plural = "s" if left != 1 else ""
    assert brief_line(cast(Any, game), target) == (
        f"HQ REQUEST  mid, {left} turn{plural} left"
    )
    assert intel_line(cast(Any, game), target) == f"Yes (mid), {left} turn{plural} left"
    other = next(t for t in targets if t.name not in _names(game))
    assert brief_line(cast(Any, game), other) is None
    assert intel_line(cast(Any, game), other) is None
