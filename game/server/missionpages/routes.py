"""The last generated mission's kneeboard pages and briefing picture (§115).

Pages are addressed by deck and page index into the generator's own record
(``game/retlab/mission_pages.py``), never by a path, so nothing outside what that
generation wrote can be served.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from game.retlab.mission_pages import last_mission_pages
from .models import KneeboardDeckJs, MissionPagesJs

router: APIRouter = APIRouter(prefix="/mission-pages")

_MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def _image(path: Path) -> FileResponse:
    media_type = _MEDIA_TYPES.get(path.suffix.lower())
    if media_type is None or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    # The same URL shows a new page after the next generation.
    return FileResponse(
        path, media_type=media_type, headers={"Cache-Control": "no-store"}
    )


@router.get("/", operation_id="get_mission_pages", response_model=MissionPagesJs)
def get_mission_pages() -> MissionPagesJs:
    pages = last_mission_pages()
    if pages is None:
        return MissionPagesJs(generated_at=None, decks=[], has_briefing=False)
    return MissionPagesJs(
        generated_at=pages.generated_at,
        decks=[
            KneeboardDeckJs(name=deck.name, page_count=len(deck.pages))
            for deck in pages.decks
        ],
        has_briefing=pages.briefing is not None and pages.briefing.is_file(),
    )


@router.get(
    "/kneeboard/{deck}/{page}",
    operation_id="get_kneeboard_page",
    response_class=FileResponse,
)
def get_kneeboard_page(deck: int, page: int) -> FileResponse:
    pages = last_mission_pages()
    if pages is None or not 0 <= deck < len(pages.decks):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    deck_pages = pages.decks[deck].pages
    if not 0 <= page < len(deck_pages):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _image(deck_pages[page])


@router.get(
    "/briefing", operation_id="get_briefing_picture", response_class=FileResponse
)
def get_briefing_picture() -> FileResponse:
    pages = last_mission_pages()
    if pages is None or pages.briefing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _image(pages.briefing)
