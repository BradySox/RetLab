"""A real campaign for the AI link's tests, built once per test run.

Fakes only show a view what the test thought to fake. ``tools/_campaign_game.py``
builds a fresh game from a shipped campaign the fork did not author, with both
sides' first turn planned. It takes about 15 seconds, so it is session-scoped:
tests must put back anything they change on it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

CAMPAIGN = "northern_russia"


@pytest.fixture(scope="session")
def campaign_game(tmp_path_factory: pytest.TempPathFactory) -> Any:
    path = Path("tools/_campaign_game.py").resolve()
    spec = importlib.util.spec_from_file_location("_campaign_game", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_game(CAMPAIGN, str(tmp_path_factory.mktemp("ai-link")))
