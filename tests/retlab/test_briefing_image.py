"""Tests for the briefing-screen picture (§107)."""

from __future__ import annotations

from pathlib import Path

from game.retlab.briefing_image import (
    DEFAULT_BRIEFING_IMAGE,
    briefing_image_path,
)


def test_default_image_ships() -> None:
    assert DEFAULT_BRIEFING_IMAGE.is_file()


def test_no_user_file_uses_default(tmp_path: Path) -> None:
    assert briefing_image_path(tmp_path) == DEFAULT_BRIEFING_IMAGE.resolve()


def test_user_png_wins(tmp_path: Path) -> None:
    (tmp_path / "briefing.png").write_bytes(b"png")
    assert briefing_image_path(tmp_path) == (tmp_path / "briefing.png").resolve()


def test_user_jpg_is_found(tmp_path: Path) -> None:
    (tmp_path / "briefing.jpg").write_bytes(b"jpg")
    assert briefing_image_path(tmp_path) == (tmp_path / "briefing.jpg").resolve()


def test_png_preferred_over_jpg(tmp_path: Path) -> None:
    (tmp_path / "briefing.jpg").write_bytes(b"jpg")
    (tmp_path / "briefing.png").write_bytes(b"png")
    assert briefing_image_path(tmp_path).name == "briefing.png"


def test_a_folder_named_like_the_image_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "briefing.png").mkdir()
    assert briefing_image_path(tmp_path) == DEFAULT_BRIEFING_IMAGE.resolve()
