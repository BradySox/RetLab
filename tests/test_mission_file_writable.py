from pathlib import Path

import pytest

from game.persistency import mission_file_writable


def test_missing_file_is_writable(tmp_path: Path) -> None:
    assert mission_file_writable(tmp_path / "retribution_nextturn.miz")


def test_existing_file_is_writable_and_left_intact(tmp_path: Path) -> None:
    path = tmp_path / "retribution_nextturn.miz"
    path.write_bytes(b"last turn")
    assert mission_file_writable(path)
    assert path.read_bytes() == b"last turn"


def test_locked_file_is_not_writable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "retribution_nextturn.miz"
    path.write_bytes(b"last turn")

    def locked(*args: object, **kwargs: object) -> None:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "open", locked)
    assert not mission_file_writable(path)
