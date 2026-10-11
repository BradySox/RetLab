"""Nothing the outside AI can read carries blue's plan.

The rule the AI link stands on is that blue's ATO is the human's private side of
the board. ``test_read_api`` pins that asking for blue is refused. This pins the
other half, against a real campaign: every GET route is called for red, with
blue's ATO swapped for a tripwire, and again with marker values planted on blue's
packages, flights and budget that must not appear in any response. A GET route
added later is picked up from the router; one this test cannot call fails it.

The idea is from Hussar2477/dcs-retribution's ``llm-ai-opponent`` branch.
"""

from __future__ import annotations

import inspect
import json
from types import SimpleNamespace
from typing import Any, Iterator, cast

import pytest
from fastapi.encoders import jsonable_encoder

from game.server import GameContext
from game.server.retributionai.routes import router

PACKAGE_MARKER = "ZZBLUEPACKAGE"
FLIGHT_MARKER = "ZZBLUEFLIGHT"
BUDGET_MARKER = 987654321


@pytest.fixture(scope="module")
def game(campaign_game: Any) -> Iterator[Any]:
    previous = getattr(GameContext, "_game_model", None)
    GameContext.set_model(cast(Any, SimpleNamespace(game=campaign_game)))
    try:
        yield campaign_game
    finally:
        GameContext.set_model(cast(Any, previous))


class _Tripwire:
    """Stands in for blue's ATO: any use of it is a leak."""

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"a red read touched blue's ATO ({name})")


def _get_routes() -> list[Any]:
    return [r for r in router.routes if "GET" in getattr(r, "methods", ())]


def _red_flight_ids(game: Any) -> list[str]:
    return [str(f.id) for p in game.red.ato.packages for f in p.flights]


def _calls(game: Any, extra_flight_ids: list[str]) -> Iterator[tuple[str, Any]]:
    """Every GET route as (label, zero-argument call)."""
    request = SimpleNamespace(base_url="http://localhost:16880/")
    for route in _get_routes():
        endpoint = route.endpoint
        params = inspect.signature(endpoint).parameters
        if route.path.endswith("/waypoints/{flight_id}"):
            for flight_id in _red_flight_ids(game) + extra_flight_ids:
                yield f"{route.path} {flight_id}", lambda f=flight_id: endpoint(f)
            continue
        required = [
            name
            for name, param in params.items()
            if param.default is inspect.Parameter.empty
        ]
        if required == ["request"]:
            yield route.path, lambda: endpoint(request)
        elif not required:
            yield route.path, endpoint
        else:
            raise AssertionError(
                f"{route.path} needs {required}: teach this test how to call it"
            )


def _text(result: Any) -> str:
    body = getattr(result, "body", None)
    if isinstance(body, (bytes, bytearray)):
        # A Response. The PNG map cannot be scanned; the tripwire covers it.
        if str(getattr(result, "media_type", "")).startswith("image"):
            return ""
        return body.decode("utf-8", errors="ignore")
    return json.dumps(jsonable_encoder(result))


def _served(game: Any, extra_flight_ids: list[str]) -> dict[str, str]:
    """Every response as text. A refusal is a response too, and is kept."""
    from fastapi import HTTPException

    out: dict[str, str] = {}
    for label, call in _calls(game, extra_flight_ids):
        try:
            out[label] = _text(call())
        except (HTTPException, KeyError) as refused:
            out[label] = str(refused)
    return out


def test_the_campaign_gives_both_sides_something_to_hide(game: Any) -> None:
    assert game.blue.ato.packages
    assert any(p.flights for p in game.blue.ato.packages)
    assert len(_get_routes()) >= 10


def test_no_red_read_touches_blues_ato(game: Any) -> None:
    real = game.blue.ato
    game.blue.ato = _Tripwire()
    try:
        served = _served(game, [])
    finally:
        game.blue.ato = real
    # The reads really ran: red's turn is a long document.
    turn_context = next(
        text for label, text in served.items() if "turn_context" in label
    )
    assert len(turn_context) > 1000


def test_the_markers_would_show_in_a_blue_read(game: Any) -> None:
    """The scan has teeth: the same view built for blue does carry a marker."""
    from game.agent import views

    flight = next(f for p in game.blue.ato.packages for f in p.flights)
    blue_read = json.dumps(jsonable_encoder(views.build_packages(game, "blue")))
    assert str(flight.id) in blue_read


def test_markers_planted_on_blue_reach_no_response(game: Any) -> None:
    blue = game.blue
    blue_flights = [f for p in blue.ato.packages for f in p.flights]
    old_budget = blue.budget
    old_names = [(p, p.custom_name) for p in blue.ato.packages]
    old_flight_names = [(f, f.custom_name) for f in blue_flights]
    blue.budget = float(BUDGET_MARKER)
    for index, package in enumerate(blue.ato.packages):
        package.custom_name = f"{PACKAGE_MARKER}{index}"
    for index, flight in enumerate(blue_flights):
        flight.custom_name = f"{FLIGHT_MARKER}{index}"
    forbidden = [PACKAGE_MARKER, FLIGHT_MARKER, str(BUDGET_MARKER)]
    forbidden += [str(flight.id) for flight in blue_flights]
    try:
        # Asking for a blue flight's route by id is refused, and says nothing.
        served = _served(game, [str(flight.id) for flight in blue_flights[:3]])
    finally:
        blue.budget = old_budget
        for package, name in old_names:
            package.custom_name = name
        for flight, name in old_flight_names:
            flight.custom_name = name

    leaks = [
        (label, marker)
        for label, text in served.items()
        for marker in forbidden
        # The refusal for a blue flight id echoes the id that was asked for.
        if marker in text and marker not in label
    ]
    assert leaks == []
