from pathlib import Path
from typing import Iterator, Tuple

import pytest

from game.campaignloader import campaign as campaign_mod
from game.campaignloader.campaign import Campaign, campaign_yaml_named


@pytest.fixture
def campaigns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Tuple[Path, list[int]]]:
    (tmp_path / "a.yaml").write_text("name: Alpha\nvictory: {a: 1}\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("name: Bravo\n", encoding="utf-8")
    (tmp_path / "bad.yaml").write_text("name: [unclosed\n", encoding="utf-8")
    (tmp_path / "dup.yaml").write_text("name: Alpha\nfrom: dup\n", encoding="utf-8")
    scans: list[int] = []

    def defs() -> Iterator[Path]:
        scans.append(1)
        yield from sorted(tmp_path.glob("*.yaml"))

    monkeypatch.setattr(Campaign, "iter_campaign_defs", staticmethod(defs))
    monkeypatch.setattr(campaign_mod, "_PATHS_BY_NAME", None)
    yield tmp_path, scans


def test_finds_by_name_and_first_file_wins(campaigns: Tuple[Path, list[int]]) -> None:
    assert campaign_yaml_named("Alpha") == {"name": "Alpha", "victory": {"a": 1}}
    assert campaign_yaml_named("Bravo") == {"name": "Bravo"}


def test_unknown_or_empty_name_is_none(campaigns: Tuple[Path, list[int]]) -> None:
    assert campaign_yaml_named("Charlie") is None
    assert campaign_yaml_named("") is None
    assert campaign_yaml_named(None) is None


def test_scans_once_and_rereads_the_file(campaigns: Tuple[Path, list[int]]) -> None:
    folder, scans = campaigns
    campaign_yaml_named("Alpha")
    (folder / "b.yaml").write_text("name: Bravo\nedited: true\n", encoding="utf-8")
    assert campaign_yaml_named("Bravo") == {"name": "Bravo", "edited": True}
    assert len(scans) == 1
