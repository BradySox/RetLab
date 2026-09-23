from typing import Any, Optional, cast

from game.commander.objectivefinder import ObjectiveFinder
from game.retlab.hq_priorities import (
    BOTTOM_FACTOR,
    TOP_FACTOR,
    HqStandings,
    importance_of,
    planning_enabled,
    why_it_matters,
)
from game.theater.player import Player


class FakeSettings:
    def __init__(self, on: bool = True, c2: bool = False) -> None:
        self.hq_priority_targets = on
        self.c2_decapitation_effects = c2
        self.enemy_income_multiplier = 1.0


class FakeUnit:
    def __init__(self, alive: bool = True) -> None:
        self.alive = alive


class FakeControlPoint:
    def __init__(self, captured: Player = Player.RED) -> None:
        self.captured = captured
        self.ground_objects: list[Any] = []
        self.coalition = object()
        self.active_ammo_depots_count = 0

    def deployable_front_line_units_with(self, depots: int) -> int:
        return min(40, 10 + 8 * depots)


class FakeTgo:
    def __init__(
        self,
        cp: FakeControlPoint,
        category: str,
        buildings: int = 1,
        value: int = 0,
        hidden: bool = False,
        known: bool = True,
    ) -> None:
        self.control_point = cp
        self.category = category
        self.statics = [FakeUnit() for _ in range(buildings)]
        self.value = value
        self.hidden = hidden
        self.known = known
        self.coalition = cp.coalition
        cp.ground_objects.append(self)

    def is_dead(self) -> bool:
        return False

    def alive_unit_count(self) -> int:
        return len(self.statics)

    def hidden_on_player_map(self, viewer: Player) -> bool:
        return self.hidden

    def known_for(self, viewer: Player) -> bool:
        return self.known


class FakeTheater:
    def __init__(self, *cps: FakeControlPoint) -> None:
        self.controlpoints = list(cps)


class FakeGame:
    def __init__(self, settings: FakeSettings, *cps: FakeControlPoint) -> None:
        self.settings = settings
        self.theater = FakeTheater(*cps)


def _game(settings: Optional[FakeSettings] = None) -> tuple[FakeGame, FakeControlPoint]:
    cp = FakeControlPoint()
    return FakeGame(settings or FakeSettings(), cp), cp


def _standings(game: FakeGame) -> HqStandings:
    return HqStandings(cast(Any, game))


def test_income_building_is_measured_in_enemy_income() -> None:
    game, cp = _game()
    factory = FakeTgo(cp, "factory", buildings=2)
    importance = importance_of(factory, cast(Any, game))
    assert importance is not None
    assert importance.score == 5.0
    assert importance.reason == "$5.0M a turn of enemy income"


def test_a_family_is_split_into_thirds() -> None:
    game, cp = _game()
    low = FakeTgo(cp, "factory", buildings=1)
    mid = FakeTgo(cp, "factory", buildings=2)
    high = FakeTgo(cp, "oil", buildings=1)
    standings = _standings(game)
    assert standings.factor(high) == TOP_FACTOR
    assert standings.factor(mid) == 1.0
    assert standings.factor(low) == BOTTOM_FACTOR


def test_ties_share_a_tier() -> None:
    game, cp = _game()
    top = [FakeTgo(cp, "factory", buildings=2) for _ in range(3)]
    bottom = [FakeTgo(cp, "factory", buildings=1) for _ in range(3)]
    standings = _standings(game)
    assert all(standings.factor(t) == TOP_FACTOR for t in top)
    assert all(standings.factor(t) == BOTTOM_FACTOR for t in bottom)


def test_an_unmeasured_target_stays_neutral_and_is_not_counted() -> None:
    game, cp = _game()
    power = FakeTgo(cp, "power")
    for buildings in (1, 2, 3):
        FakeTgo(cp, "factory", buildings=buildings)
    standings = _standings(game)
    assert standings.factor(power) == 1.0
    standing = standings.standing(power)
    assert standing is not None and standing.of == 0


def test_a_family_under_three_is_not_ranked() -> None:
    game, cp = _game()
    a = FakeTgo(cp, "factory", buildings=1)
    b = FakeTgo(cp, "factory", buildings=4)
    standings = _standings(game)
    assert standings.factor(a) == standings.factor(b) == 1.0


def test_a_site_hidden_on_the_map_is_neither_ranked_nor_weighted() -> None:
    game, cp = _game()
    hidden = FakeTgo(cp, "oil", buildings=5, hidden=True)
    for buildings in (1, 2, 3):
        FakeTgo(cp, "factory", buildings=buildings)
    standings = _standings(game)
    assert standings.standing(hidden) is None
    assert standings.factor(hidden) == 1.0


def test_friendly_targets_are_not_ranked() -> None:
    blue_cp = FakeControlPoint(Player.BLUE)
    game = FakeGame(FakeSettings(), blue_cp)
    own = FakeTgo(blue_cp, "factory")
    assert _standings(game).standing(own) is None


def test_ammo_depot_is_measured_in_front_line_vehicles() -> None:
    game, cp = _game()
    cp.active_ammo_depots_count = 3
    depot = FakeTgo(cp, "ammo", buildings=2)
    importance = importance_of(depot, cast(Any, game))
    assert importance is not None
    # 34 fielded with three depots' worth, 18 with one.
    assert importance.score == 16.0


def test_command_post_is_neutral_while_its_effects_are_off() -> None:
    game, cp = _game(FakeSettings(c2=False))
    post = FakeTgo(cp, "commandcenter")
    importance = importance_of(post, cast(Any, game))
    assert importance is not None and importance.score is None


def test_equipment_is_measured_by_price() -> None:
    game, cp = _game()
    sam = FakeTgo(cp, "aa", value=120)
    importance = importance_of(sam, cast(Any, game))
    assert importance is not None
    assert importance.reason == "$120M of equipment"


def test_only_blue_with_the_setting_on_plans_with_it() -> None:
    game, _ = _game(FakeSettings(on=True))
    assert planning_enabled(cast(Any, game), is_blue=True)
    assert not planning_enabled(cast(Any, game), is_blue=False)
    game_off, _ = _game(FakeSettings(on=False))
    assert not planning_enabled(cast(Any, game_off), is_blue=True)


def test_the_objective_finder_applies_it_for_blue_only() -> None:
    game, cp = _game()
    targets = [FakeTgo(cp, "factory", buildings=b) for b in (1, 2, 3)]
    blue = ObjectiveFinder(cast(Any, game), Player.BLUE)
    red = ObjectiveFinder(cast(Any, game), Player.RED)
    assert blue._hq_factor(cast(Any, targets[2])) == TOP_FACTOR
    assert red._hq_factor(cast(Any, targets[2])) == 1.0


def test_the_panel_line_names_the_rank() -> None:
    game, cp = _game()
    targets = [FakeTgo(cp, "factory", buildings=b) for b in (1, 2, 3)]
    line = why_it_matters(targets[2], cast(Any, game), Player.BLUE)
    assert line == "$7.5M a turn of enemy income. #1 of 3 infrastructure targets"


def test_the_panel_line_keeps_an_unengaged_site_unknown() -> None:
    game, cp = _game()
    site = FakeTgo(cp, "aa", value=120, known=False)
    assert why_it_matters(site, cast(Any, game), Player.BLUE) == "Unknown (not engaged)"


def test_the_panel_line_is_blue_looking_at_red_only() -> None:
    game, cp = _game()
    site = FakeTgo(cp, "aa", value=120)
    assert why_it_matters(site, cast(Any, game), Player.RED) is None


class FakeGroup:
    def __init__(self) -> None:
        self.units = [FakeUnit()]


class FakeCoalition:
    player = Player.RED


def test_command_post_is_measured_in_offensive_packages() -> None:
    game, cp = _game(FakeSettings(c2=True))
    cp.coalition = FakeCoalition()
    posts = [FakeTgo(cp, "commandcenter") for _ in range(3)]
    for post in posts:
        post.groups = [FakeGroup()]  # type: ignore[attr-defined]
    importance = importance_of(posts[0], cast(Any, game))
    assert importance is not None
    assert importance.score == 4.0
    assert importance.reason == "Enemy offensive package ceiling falls from 12 to 8"
