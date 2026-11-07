"""Every squadron preset loads, and no livery set repeats a livery.

A preset that fails to load stops the squadron list loading for every faction,
and a repeated livery in a set puts the same paint on two jets.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterator

import pytest

from game import persistency
from game.squadrons.squadrondef import SquadronDef

PRESETS = sorted(Path("resources/squadrons").glob("*/*.yaml"))


@pytest.fixture(scope="module")
def presets(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[list[tuple[Path, SquadronDef]]]:
    tmp_path: Path = tmp_path_factory.mktemp("squadron_presets")
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16885)
    yield [(path, SquadronDef.from_yaml(path)) for path in PRESETS]


def test_every_preset_loads(presets: list[tuple[Path, SquadronDef]]) -> None:
    assert len(presets) == len(PRESETS)


def test_no_livery_repeats_in_a_set(presets: list[tuple[Path, SquadronDef]]) -> None:
    repeats = {
        str(path): sorted(livery for livery, n in Counter(lower).items() if n > 1)
        for path, squadron in presets
        if len(set(lower := [x.lower() for x in squadron.livery_set]))
        != len(squadron.livery_set)
    }
    assert not repeats
