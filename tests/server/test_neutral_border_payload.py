"""§98: the neutral-border map payload the planning UI draws.

The border is authored in terrain XY and drawn by Leaflet in lat/lng, so the
conversion is the thing worth pinning: a silently wrong transform puts a
44-vertex ring somewhere plausible-looking and nobody notices until a player
routes around empty sky. The Lebanon fixture's real bounding box is the oracle.
"""

from __future__ import annotations

import dataclasses

from datetime import date
from types import SimpleNamespace
from typing import Any

from dcs.mapping import Point
from dcs.terrain.syria import Syria
from shapely.geometry import MultiPolygon, Polygon

from game.server.game.models import NeutralBorderJs
from game.theater.neutralborder import NeutralBorderZone

# Lebanon's real extent, with a 0.1 degree (~11 km) margin. Tight enough that a
# broken transform cannot pass -- those land in the wrong country or the wrong
# hemisphere, not 11 km off -- and loose enough not to be brittle against the
# simplifier's vertex placement.
MARGIN = 0.1
LEBANON_LAT = (33.05 - MARGIN, 34.69 + MARGIN)
LEBANON_LNG = (35.10 - MARGIN, 36.62 + MARGIN)


def _zone() -> NeutralBorderZone:
    zone = NeutralBorderZone.from_yaml(
        {
            "country": "Lebanon",
            "airfield": "Rayak",
            "floor_ft": 10000,
            "sam": True,
            # A coarse box inside Lebanon is enough to prove the transform; the
            # shipped campaign carries the real 44-vertex trace.
            "border": [
                [-37713, 38996],
                [-211351, -80947],
                [-217426, -55276],
                [-44380, 42821],
            ],
        }
    )
    assert zone is not None
    return zone


def _game(enabled: bool = True, zones: list[Any] | None = None) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(neutral_border_defense=enabled),
        current_day=date(2022, 6, 4),
        blue=SimpleNamespace(faction=SimpleNamespace(country=None)),
        theater=SimpleNamespace(
            neutral_border_zones=[_zone()] if zones is None else zones,
            terrain=Syria(),
        ),
    )


def test_border_converts_to_real_lebanese_coordinates() -> None:
    borders = NeutralBorderJs.all_in_game(_game())
    assert len(borders) == 1
    border = borders[0]
    assert border.country == "Lebanon"
    # The tooltip names what defends the airspace, not a field: nothing has
    # launched from one since the patrol went (2026-09-09).
    assert "batteries" in border.airfield
    assert border.floor_ft == 10000

    # One ring, no holes -- the Leaflet array-of-arrays contract.
    assert len(border.border) == 1
    ring = border.border[0]
    assert len(ring) == 4

    lats = [p.lat for p in ring]
    lngs = [p.lng for p in ring]
    assert LEBANON_LAT[0] <= min(lats) and max(lats) <= LEBANON_LAT[1]
    assert LEBANON_LNG[0] <= min(lngs) and max(lngs) <= LEBANON_LNG[1]


def test_setting_off_hides_the_layer() -> None:
    assert NeutralBorderJs.all_in_game(_game(enabled=False)) == []


def test_no_authored_zones_hides_the_layer() -> None:
    assert NeutralBorderJs.all_in_game(_game(zones=[])) == []


def test_theater_without_the_attribute_is_tolerated() -> None:
    """An old save predates neutral_border_zones; the payload must not raise."""
    game = SimpleNamespace(
        settings=SimpleNamespace(neutral_border_defense=True),
        current_day=date(2022, 6, 4),
        blue=SimpleNamespace(faction=SimpleNamespace(country=None)),
        theater=SimpleNamespace(terrain=Syria()),
    )
    assert NeutralBorderJs.all_in_game(game) == []  # type: ignore[arg-type]


# -- the map must not promise an interception the mission will not fly ----------


def _toothless_zone() -> NeutralBorderZone:
    """A neutral with NO origin, which is the only way to be toothless now.

    It used to mean "no era airframe" as well, which covered 14 zones. Dropping
    the fighter patrol on 2026-09-07 widened the feature: a SAM needs no airframe
    and no runway, so Turkmenistan, Cyprus, Armenia and Azerbaijan all defend
    today. Only a zone with nowhere to stand a battery is drawn and toothless.
    """
    zone = NeutralBorderZone.from_yaml(
        {
            "country": "Turkmenistan",
            "border": [
                [-37713, 38996],
                [-211351, -80947],
                [-217426, -55276],
                [-44380, 42821],
            ],
        }
    )
    assert zone is not None
    return zone


def test_a_country_that_cannot_defend_is_not_drawn_as_closed() -> None:
    """The generator degrades it to drawn-and-toothless, so the map has to agree.

    It did not until 2026-08-27: the map computed enforcement from posture and
    consent alone and never asked whether the country could defend at all, so
    zones were drawn "closed to you at any altitude" over a mission that let you
    fly straight through them. The feature exists to be planned against, so
    overstating the threat is the expensive direction of wrong: you route around
    nothing and stop trusting the layer.
    """
    borders = NeutralBorderJs.all_in_game(_game(zones=[_toothless_zone()]))
    assert len(borders) == 1
    assert borders[0].overflight is True, "a country that cannot defend read closed"
    assert "permitted" in borders[0].airfield


def test_a_country_that_can_defend_is_still_drawn_as_closed() -> None:
    """The control: the fix must not open every border it touches."""
    borders = NeutralBorderJs.all_in_game(_game())
    assert len(borders) == 1
    assert borders[0].overflight is False, "a defended border was opened"


def test_a_border_past_the_land_map_is_drawn_only_to_its_edge() -> None:
    """Territory and sectors stop at the land map's edge; the border must too.

    Syria's land map ends at 31.3E while the shipped Turkey border runs to
    29.5E, which drew a strip of Turkey the sector fill never reached.
    """
    zone = dataclasses.replace(
        _zone(),
        border=[(0.0, 0.0), (0.0, 100_000.0), (50_000.0, 100_000.0), (50_000.0, 0.0)],
    )
    game = _game(zones=[zone])
    game.theater.landmap = SimpleNamespace(
        inclusion_zones=MultiPolygon(
            [Polygon([(-1e6, 40_000), (-1e6, 1e6), (1e6, 1e6), (1e6, 40_000)])]
        )
    )
    borders = NeutralBorderJs.all_in_game(game)
    assert len(borders) == 1
    ring = borders[0].border[0]
    edge = Point(25_000, 40_000, Syria()).latlng().lng
    assert min(p.lng for p in ring) >= edge - 0.01, "the border ran past the land map"
