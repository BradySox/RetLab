"""The phone's kneeboard tab (§115) serves only what the last generation recorded."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from game.retlab import mission_pages
from game.retlab.mission_pages import (
    Deck,
    last_mission_pages,
    record_briefing_picture,
    record_kneeboards,
)
from game.server.missionpages import routes


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "kneeboards"
    monkeypatch.setattr(routes, "last_mission_pages", lambda: last_mission_pages(root))
    return root


def _page(root: Path, name: str) -> Path:
    path = root / "F-16C_50" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG")
    return path


def test_nothing_generated_lists_nothing(root: Path) -> None:
    listing = routes.get_mission_pages()
    assert listing.decks == [] and not listing.has_briefing
    assert listing.generated_at is None


def test_only_the_recorded_pages_are_listed_and_served(root: Path) -> None:
    first, second = _page(root, "page00.png"), _page(root, "page01.png")
    # A longer deck from an earlier mission left this page behind.
    _page(root, "page02.png")
    record_kneeboards([Deck("F-16CM", [first, second])], root)

    listing = routes.get_mission_pages()
    assert [(d.name, d.page_count) for d in listing.decks] == [("F-16CM", 2)]
    assert Path(routes.get_kneeboard_page(0, 1).path) == second.resolve()
    for deck, page in ((0, 2), (1, 0), (-1, 0)):
        with pytest.raises(HTTPException):
            routes.get_kneeboard_page(deck, page)


def test_the_briefing_picture_joins_the_record(root: Path, tmp_path: Path) -> None:
    record_kneeboards([], root)
    picture = tmp_path / "card.png"
    picture.write_bytes(b"\x89PNG")
    record_briefing_picture(picture, root)
    assert routes.get_mission_pages().has_briefing
    assert Path(routes.get_briefing_picture().path) == picture.resolve()


def test_a_new_kneeboard_record_drops_the_old_briefing(
    root: Path, tmp_path: Path
) -> None:
    picture = tmp_path / "card.png"
    picture.write_bytes(b"\x89PNG")
    record_briefing_picture(picture, root)
    record_kneeboards([], root)
    with pytest.raises(HTTPException):
        routes.get_briefing_picture()


def test_a_malformed_record_reads_as_nothing(root: Path) -> None:
    root.mkdir()
    (root / mission_pages._MANIFEST).write_text('{"decks": 3}', encoding="utf-8")
    assert last_mission_pages(root) is None
