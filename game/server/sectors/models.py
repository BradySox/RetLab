"""§111 territory and sectors for the web map. Display only.

Not fogged: who holds the ground follows from the bases and fronts, which the
map already shows.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel
from shapely.geometry import MultiPolygon

from game.server.leaflet import LeafletLine, LeafletPoint, LeafletPoly, ShapelyUtil

if TYPE_CHECKING:
    from game import Game


class TerritoryJs(BaseModel):
    """Each side's ground; a polygon's later rings are pockets of the other side."""

    blue: list[LeafletPoly]
    red: list[LeafletPoly]

    class Config:
        title = "Territory"

    @staticmethod
    def from_game(game: Game) -> TerritoryJs:
        from game.theater.sectors import BLUE, RED, territory_for

        try:
            territory = territory_for(game.theater)
        except Exception:
            logging.exception("Territory could not be built for the map")
            return TerritoryJs(blue=[], red=[])
        theater = game.theater
        return TerritoryJs(
            blue=ShapelyUtil.polys_to_leaflet(
                MultiPolygon(territory.polygons(BLUE)), theater
            ),
            red=ShapelyUtil.polys_to_leaflet(
                MultiPolygon(territory.polygons(RED)), theater
            ),
        )


class SectorJs(BaseModel):
    name: str
    #: "blue", "red" or "none": whoever holds most of it.
    owner: str
    position: LeafletPoint

    class Config:
        title = "Sector"


class SectorsJs(BaseModel):
    """Sector names and the edges between sectors."""

    edges: list[LeafletLine]
    sectors: list[SectorJs]

    class Config:
        title = "Sectors"

    @staticmethod
    def from_game(game: Game) -> SectorsJs:
        from dcs.mapping import Point

        from game.theater.sectors import BLUE, sector_map_for, territory_for

        try:
            sector_map = sector_map_for(game.theater)
            owners = sector_map.owners(territory_for(game.theater))
            edges = sector_map.edges
        except Exception:
            logging.exception("Sectors could not be built for the map")
            return SectorsJs(edges=[], sectors=[])
        theater = game.theater
        sectors = []
        for sector in sector_map.sectors:
            owner = owners.get(sector.id)
            x, y = sector.seed
            sectors.append(
                SectorJs(
                    name=sector.name,
                    owner=(
                        "none" if owner is None else "blue" if owner == BLUE else "red"
                    ),
                    position=LeafletPoint.from_latlng(
                        Point(x, y, theater.terrain).latlng()
                    ),
                )
            )
        lines = (
            ShapelyUtil.lines_to_leaflet(edges, theater) if not edges.is_empty else []
        )
        return SectorsJs(edges=lines, sectors=sectors)
