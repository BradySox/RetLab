from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class KneeboardDeckJs(BaseModel):
    name: str
    page_count: int


class MissionPagesJs(BaseModel):
    generated_at: Optional[str]
    decks: list[KneeboardDeckJs]
    has_briefing: bool

    class Config:
        title = "MissionPages"
