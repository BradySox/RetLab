"""What the last generated mission put on the kneeboard and the briefing screen.

The phone map (§115) shows them. Kneeboard pages stay in ``kneeboards/`` after
Take Off, but a deck with fewer pages than last time leaves the old tail behind,
so the generator records exactly what it handed DCS and the phone reads only that.
See docs/dev/design/retlab-phone-map-notes.md.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

GENERATED_KNEEBOARDS_DIR = Path("kneeboards")
_MANIFEST = "phone.json"


@dataclass(frozen=True)
class Deck:
    name: str
    pages: list[Path]


@dataclass(frozen=True)
class MissionPages:
    generated_at: str
    decks: list[Deck]
    briefing: Optional[Path]


def _manifest_path(root: Path) -> Path:
    return root / _MANIFEST


def record_kneeboards(decks: list[Deck], root: Path = GENERATED_KNEEBOARDS_DIR) -> None:
    """Starts a new record: the kneeboard generator runs before the briefing's."""
    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "decks": [
            {"name": deck.name, "pages": [str(page.resolve()) for page in deck.pages]}
            for deck in decks
        ],
        "briefing": None,
    }
    _write(root, data)


def record_briefing_picture(
    picture: Path, root: Path = GENERATED_KNEEBOARDS_DIR
) -> None:
    data = _read(root) or {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "decks": [],
    }
    data["briefing"] = str(picture.resolve())
    _write(root, data)


def last_mission_pages(root: Path = GENERATED_KNEEBOARDS_DIR) -> Optional[MissionPages]:
    data = _read(root)
    if data is None:
        return None
    try:
        decks = [
            Deck(str(deck["name"]), [Path(page) for page in deck["pages"]])
            for deck in data["decks"]
        ]
        briefing = data.get("briefing")
        return MissionPages(
            str(data["generated_at"]),
            decks,
            Path(briefing) if briefing else None,
        )
    except (KeyError, TypeError):
        logging.warning("Ignoring a malformed %s", _manifest_path(root))
        return None


def _read(root: Path) -> Optional[dict[str, Any]]:
    path = _manifest_path(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _write(root: Path, data: dict[str, Any]) -> None:
    # The phone is a convenience; a failed record never fails a generation.
    try:
        root.mkdir(parents=True, exist_ok=True)
        _manifest_path(root).write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
        logging.exception("Could not record the mission's pages for the phone")
