"""A real campaign for the AI link's tests, built once for this package.

Fakes only show a view what the test thought to fake. ``tools/_campaign_game.py``
builds a fresh game from a shipped campaign the fork did not author, with both
sides' first turn planned. It takes about 15 seconds, so every test here shares
it: put back anything you change on it.

Building a game fills pydcs's per-airframe payload cache. It is pointed at the
repo's payloads first, as the app does at start, and emptied afterwards, so the
loadout tests that run later scan for themselves.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Iterator

import pytest
from dcs.payloads import PayloadDirectories
from dcs.unittype import FlyingType

CAMPAIGN = "northern_russia"
PAYLOADS = Path("resources/customized_payloads")


def _flying_types(base: type = FlyingType) -> Iterator[type]:
    for sub in base.__subclasses__():
        yield sub
        yield from _flying_types(sub)


def _forget_payloads() -> None:
    FlyingType._payload_cache = None  # type: ignore[assignment]
    for flying_type in _flying_types():
        if "payloads" in vars(flying_type):
            flying_type.payloads = None  # type: ignore[attr-defined]


@pytest.fixture(scope="package")
def campaign_game(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Any]:
    path = Path("tools/_campaign_game.py").resolve()
    spec = importlib.util.spec_from_file_location("_campaign_game", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    fallback, preferred = PayloadDirectories.fallback, PayloadDirectories.preferred
    _forget_payloads()
    PayloadDirectories.set_fallback(PAYLOADS.resolve())
    try:
        yield module.build_game(CAMPAIGN, str(tmp_path_factory.mktemp("ai-link")))
    finally:
        PayloadDirectories.fallback = fallback
        PayloadDirectories.preferred = preferred
        _forget_payloads()
