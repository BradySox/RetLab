"""An alert (QRA) template wears its squadron's paint.

The alert and §61 host-scramble templates never pass through
``FlightGroupConfigurator``, which is where a fragged flight is painted, and every
scramble clone copies its template. In test 62 (2026-10-18) the Israeli and Turkish
alert F-16s and F-4Es launched in stock paint. Building a real template needs a whole game, so this pins the call.
"""

from __future__ import annotations

import ast
import inspect
import textwrap

import pytest

from game.missiongenerator.aircraft.aircraftgenerator import AircraftGenerator


@pytest.mark.parametrize(
    "method",
    [
        AircraftGenerator.spawn_intercept_templates,
        AircraftGenerator.spawn_red_scramble_templates,
    ],
)
def test_the_template_is_painted_after_its_board_numbers(method: object) -> None:
    source = textwrap.dedent(inspect.getsource(method))  # type: ignore[arg-type]
    calls = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    painted = [
        c
        for c in calls
        if c.func.attr == "apply_livery"  # type: ignore[attr-defined]
        and isinstance(c.func.value, ast.Call)  # type: ignore[attr-defined]
        and getattr(c.func.value.func, "id", None)  # type: ignore[attr-defined]
        == "AircraftPainter"
    ]
    assert len(painted) == 1
    numbered = [c for c in calls if c.func.attr == "assign"]  # type: ignore[attr-defined]
    assert numbered and numbered[0].lineno < painted[0].lineno
