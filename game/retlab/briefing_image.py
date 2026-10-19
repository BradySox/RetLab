"""The picture DCS shows on the mission briefing screen (RetLab, §107).

Drop ``briefing.png`` or ``briefing.jpg`` into ``Saved Games\\DCS\\Retribution`` and
every generated mission shows it; with no file there the mission gets a card drawn
for that mission (``briefing_card.py``), or RetLab's plain picture if drawing
fails. On-disk content is the switch, as with §42 map tiles and §43 flight
defaults, so there is no setting. The app's startup splash is not this picture.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

DEFAULT_BRIEFING_IMAGE = Path("resources/ui/retlab_briefing.png")

# First match wins. DCS shows PNG and JPEG on the briefing screen.
USER_BRIEFING_IMAGE_NAMES = ("briefing.png", "briefing.jpg", "briefing.jpeg")


def user_briefing_image(retribution_dir: Path) -> Optional[Path]:
    for name in USER_BRIEFING_IMAGE_NAMES:
        candidate = retribution_dir / name
        if candidate.is_file():
            return candidate
    return None


def custom_briefing_image(retribution_dir: Optional[Path] = None) -> Optional[Path]:
    """The player's drop-in picture, if there is one."""
    if retribution_dir is None:
        try:
            from game import persistency

            retribution_dir = persistency.base_path() / "Retribution"
        except (AssertionError, OSError):
            # persistency not set up (tests, tools): no user folder to look in.
            retribution_dir = None
    if retribution_dir is not None:
        custom = user_briefing_image(retribution_dir)
        if custom is not None:
            logging.info("Briefing image: using %s", custom)
            return custom.resolve()
    return None


def briefing_image_path(retribution_dir: Optional[Path] = None) -> Path:
    """The image to embed: the user's drop-in file, else the RetLab default."""
    custom = custom_briefing_image(retribution_dir)
    return custom if custom is not None else DEFAULT_BRIEFING_IMAGE.resolve()
