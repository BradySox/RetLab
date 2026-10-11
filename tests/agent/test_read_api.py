"""The outside AI's read API: red only, token-gated, and the briefing matches the routes."""

import re
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from game.agent import service, views
from game.server.app import app
from game.server.retributionai.routes import router
from game.server.security import ApiKeyManager


@pytest.mark.parametrize(
    "call",
    [
        lambda: service.turn_context("blue"),
        lambda: service.packages("blue"),
        lambda: service.waypoints("blue", "anything"),
        lambda: service.iads("BLUE"),
        lambda: service.map_image("blue"),
    ],
)
def test_blue_is_refused_before_the_game_is_read(call: Any) -> None:
    # No GameContext is set: the guard must refuse before it is touched.
    with pytest.raises(service.SideNotAllowedError):
        call()


def test_token_by_header_or_query() -> None:
    key = ApiKeyManager.KEY
    ApiKeyManager.verify(key, None)
    ApiKeyManager.verify(None, key)
    for header, query in ((None, None), ("wrong", None), (None, "wrong")):
        with pytest.raises(HTTPException) as raised:
            ApiKeyManager.verify(header, query)
        assert raised.value.status_code == 403


def test_every_ai_route_needs_the_token_and_the_map_routes_do_not() -> None:
    assert [d.dependency for d in router.dependencies] == [ApiKeyManager.verify]
    ai_paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/retribution-ai/turn_context" in ai_paths
    # The map server's own routes were open before this and stay open.
    tgos = next(r for r in app.routes if getattr(r, "path", "") == "/tgos/")
    assert not getattr(tgos, "dependencies", [])


def test_the_briefing_names_only_routes_that_exist() -> None:
    text = service.start_doc("http://localhost:16880") + service.howtoplay_doc()
    named = set(re.findall(r"/retribution-ai/([a-z_/]+)", text))
    paths = {r.path.removeprefix("/retribution-ai/") for r in router.routes}  # type: ignore[attr-defined]
    for name in named:
        assert any(
            p == name or p.startswith(name.rstrip("/") + "/{") for p in paths
        ), name
    assert named >= {"turn_context", "packages", "prev_turns", "iads", "howtoplay"}


def test_connect_url_carries_the_token() -> None:
    url = service.connect_url()
    assert url.startswith("http://localhost:")
    assert url.endswith(f"/retribution-ai/start?token={ApiKeyManager.KEY}")


def _target(tid: str, kind: str, threat: int | None) -> views.TargetView:
    return views.TargetView(
        id=tid, name=tid, kind=kind, suggested_task="DEAD", pos=[0, 0], threat_nm=threat
    )


def test_threats_are_every_umbrella_ranked_by_reach() -> None:
    targets = [_target(f"s{i}", "sam", 24) for i in range(15)]
    targets += [
        _target("big", "sam", 80),
        _target("ship", "ship", 60),
        _target("building", "building", 5),
        _target("ewr", "sam", None),
    ]
    threats = views.build_threats(targets)
    assert [t.id for t in threats[:2]] == ["big", "ship"]
    assert len(threats) == 17


def _squadron(owned: int, untasked: int, pilots: int, reserve: int = 0) -> Any:
    location = SimpleNamespace(captured="red", runway_is_operational=lambda: True)
    return SimpleNamespace(
        owned_aircraft=owned,
        untasked_aircraft=untasked,
        number_of_available_pilots=pilots,
        pilot_limits_enabled=True,
        intercept_reserve=reserve,
        location=location,
    )


def test_flyable_is_capped_by_pilots_and_qra_is_named() -> None:
    assert views._squadron_flyable(_squadron(12, 10, 4), grounded=False) == 4
    assert views._squadron_flyable(_squadron(12, 10, 4), grounded=True) == 0
    held = _squadron(4, 0, 4, reserve=4)
    assert views._unflyable_reason(held, grounded=False) == (
        "4 held on QRA alert, the rest tasked"
    )
    assert views._unflyable_reason(_squadron(4, 0, 4), grounded=False) == (
        "all 4 already tasked"
    )


def _turn(blue: int, red: int) -> Any:
    side = lambda n: SimpleNamespace(aircraft_count=n, vehicles_count=0)
    return SimpleNamespace(allied_units=side(blue), enemy_units=side(red))


def test_prev_turns_leaves_out_the_turn_being_planned() -> None:
    game = SimpleNamespace(
        turn=2,
        game_stats=SimpleNamespace(
            data_per_turn=[_turn(10, 20), _turn(9, 18), _turn(9, 17)]
        ),
        last_sitrep=None,
        informations=[SimpleNamespace(turn=1, title="Lost", text="a jet")],
    )
    result = views.build_prev_turns(cast(Any, game), n=5)
    assert [t.turn for t in result.trend] == [0, 1]
    assert result.trend[-1].red.aircraft == 18
    assert result.events == ["Lost: a jet"]


@pytest.mark.parametrize(
    "line, expected",
    [
        (
            "Enemy reinforcements: T-55A x 2 at Alta",
            "Red reinforcements: T-55A x 2 at Alta",
        ),
        (
            "Ally reinforcements: M113 x 9 at Bardufoss",
            "Blue reinforcements: M113 x 9 at Bardufoss",
        ),
        ("We took control of Alta.", "Blue took control of Alta."),
        ("The enemy took control of Evenes.", "Red took control of Evenes."),
        (
            "Our ground forces from A reached a stalemate with enemy forces from B",
            "Blue's ground forces from A reached a stalemate with red forces from B",
        ),
        ("OPFOR has begun repairing the runway at Banak", None),
        # Whichever side owns the base: not blue's word.
        ("Alta is not connected to any friendly points.", None),
    ],
)
def test_the_campaign_log_names_the_sides(line: str, expected: str | None) -> None:
    if expected is None:
        expected = line.replace("OPFOR", "Red")
    assert views.name_the_sides(line) == expected


def _flight_with_loadout(restrict: bool) -> Any:
    planned = SimpleNamespace(
        name="Anti-ship", pylons={2: SimpleNamespace(name="Kh-31A")}
    )
    dated = SimpleNamespace(
        name="Anti-ship", pylons={2: SimpleNamespace(name="Kh-29L"), 5: None}
    )
    planned.degrade_for_date = lambda *args: dated
    game = SimpleNamespace(
        settings=SimpleNamespace(restrict_weapons_by_date=restrict), date=None
    )
    return SimpleNamespace(
        iter_members=lambda: iter([SimpleNamespace(loadout=planned)]),
        coalition=SimpleNamespace(game=game),
        unit_type=None,
        squadron=SimpleNamespace(coalition=SimpleNamespace(faction=None)),
        package=SimpleNamespace(target=None),
    )


def test_a_loadout_is_the_one_the_mission_is_built_with() -> None:
    # The date rule runs at generation, so the planned fit lists weapons never loaded.
    assert views._flight_loadout(_flight_with_loadout(True)) == (
        "Anti-ship",
        {2: "Kh-29L"},
    )
    assert views._flight_loadout(_flight_with_loadout(False)) == (
        "Anti-ship",
        {2: "Kh-31A"},
    )


def _room(parking: int, limits: bool, max_size: int, owned: int, pending: int) -> int:
    squadron: Any = SimpleNamespace(
        location=SimpleNamespace(unclaimed_parking=lambda _type: parking),
        settings=SimpleNamespace(enable_squadron_aircraft_limits=limits),
        max_size=max_size,
        owned_aircraft=owned,
        pending_deliveries=pending,
        aircraft=SimpleNamespace(
            dcs_unit_type=SimpleNamespace(helicopter=False, flyable=True)
        ),
    )
    with patch("game.theater.controlpoint.ParkingType.from_squadron", lambda *_: None):
        return views._squadron_room(squadron)


def test_a_squadrons_room_is_parking_then_its_cap() -> None:
    assert _room(parking=5, limits=False, max_size=12, owned=12, pending=0) == 5
    assert _room(parking=5, limits=True, max_size=12, owned=10, pending=1) == 1
    assert _room(parking=0, limits=True, max_size=12, owned=4, pending=0) == 0
    # Over its cap after a transfer in: never negative.
    assert _room(parking=5, limits=True, max_size=12, owned=14, pending=0) == 0


def test_every_red_squadron_says_how_many_aircraft_it_can_add(
    campaign_game: Any,
) -> None:
    squadrons = views.build_turn_context(campaign_game, "red").air_wing
    assert squadrons
    assert all(isinstance(sq.can_add, int) and sq.can_add >= 0 for sq in squadrons)
    assert "can_add" in squadrons[0].model_dump(exclude_none=True)


def test_a_front_counts_the_garrison_blocking_capture_and_lists_it(
    campaign_game: Any,
) -> None:
    from game.commander.battlepositions import BattlePositions

    targets = views.build_targets(campaign_game, "red")
    fronts = [t for t in targets if t.kind == "front"]
    garrisons = {t.id: t for t in targets if t.kind == "garrison"}
    assert fronts
    blocking_ids: set[str] = set()
    for front in fronts:
        enemy_cp = next(
            cp
            for cp in campaign_game.theater.controlpoints
            if str(cp.id) == front.enemy_cp_id
        )
        blocking = BattlePositions.for_control_point(enemy_cp).blocking_capture
        assert front.capture_blocked_by == len(blocking)
        blocking_ids |= {str(group.id) for group in blocking}
    # Every blocker can be aimed at, once, with BAI; nothing else is called a garrison.
    assert set(garrisons) == blocking_ids
    assert all(t.suggested_task == "BAI" for t in garrisons.values())
    assert len([t for t in targets if t.kind == "garrison"]) == len(garrisons)


def test_only_a_missing_campaign_answers_409(monkeypatch: pytest.MonkeyPatch) -> None:
    from game.server import GameContext
    from game.server.retributionai import routes

    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=None), raising=False
    )
    for call in (routes.capabilities, routes.settings, routes.notes):
        with pytest.raises(HTTPException) as raised:
            call()
        assert raised.value.status_code == 409

    def broken() -> None:
        raise RuntimeError("a bug, not a missing campaign")

    with pytest.raises(RuntimeError):
        routes._guarded(broken)


@pytest.mark.parametrize(
    "bbox",
    ["nan,0,1,1", "0,0,inf,1", "-inf,-inf,inf,inf", "0,0,0,1", "1,2,3", "95,0,99,1"],
)
def test_a_map_box_that_is_not_on_the_globe_is_ignored(bbox: str) -> None:
    from game.agent import mapimage

    assert mapimage._parse_bbox(bbox) is None


def test_a_map_box_is_clamped_to_the_globe(campaign_game: Any) -> None:
    from game.agent import mapimage

    whole = "-1e308,-1e308,1e308,1e308"
    assert mapimage._parse_bbox(whole) == (-90.0, -180.0, 90.0, 180.0)
    assert mapimage._parse_bbox("40,30,45,38") == (40.0, 30.0, 45.0, 38.0)
    # Unclamped, this walked the graticule loops for as long as it was left to.
    context = views.build_turn_context(campaign_game, "red")
    assert mapimage.render(context, whole).startswith(b"\x89PNG")
