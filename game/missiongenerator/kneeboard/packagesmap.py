"""The packages map: every friendly package's route and target on one chart."""

import math
from pathlib import Path
from typing import Any, List, Optional, TYPE_CHECKING, Tuple

from PIL import ImageFont

from ..kneeboard_page import KneeboardPage

if TYPE_CHECKING:
    from dcs.terrain.terrain import Terrain
from .writer import KneeboardPageWriter


def _abbreviated_target_name(name: str) -> str:
    """Shorten verbose target prefixes so long names fit the kneeboard tables.

    Front-line objectives are named "Front line <CP A>/<CP B>", wide enough to
    overflow the packages list and crowd the map labels; "Front" is
    unambiguous in context.
    """
    return name.replace("Front line ", "Front ")


class PackagesMapPage(KneeboardPage):
    """A theater map with each attack package's target labelled.

    Draws the theater terrain behind the packages so the pilot can see where
    the ones on the previous page are headed — the shipped theater raster
    where it covers the area, else filled coastlines from the landmap. Never
    the network. Control points are marked for orientation: airfields,
    carriers and LHAs get a distinct shape (square / diamond / triangle) and a
    haloed name label, while FOBs and other points stay as plain dots. All are
    coloured by side (blue friendly, red enemy). Overlapping labels are stacked
    downward (and flipped left near the right edge).
    """

    FRIENDLY = (40, 90, 200)
    ENEMY = (200, 45, 45)
    NEUTRAL = (110, 110, 110)
    TARGET = (255, 140, 0)

    #: How far a label may sit from its own marker. The search used to walk to
    #: the map edge, so a crowded cluster threw its names hundreds of pixels
    #: into open sea where they read as belonging to whatever was near them
    #: (flown 2026-08-22: eleven target names stacked in a column clear of the
    #: dots, and "King Abdullah II" printed over water).
    MAX_LABEL_OFFSET = 90
    #: Past this gap a label gets a leader line back to its marker. Below it the
    #: label is adjacent and a line would just be clutter.
    LEADER_AT = 22

    def __init__(
        self,
        targets: List[Tuple[str, float, float]],
        control_points: List[Tuple[float, float, str, str, str]],
        terrain: "Terrain",
        dark_kneeboard: bool,
    ) -> None:
        self.targets = targets
        self.control_points = control_points
        self.terrain = terrain
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        from dcs.mapping import Point as DcsPoint
        from ..kneeboard_recon.basemap import (
            align_extent_to_theater_raster,
            render_theater_basemap,
        )
        from ..kneeboard_recon.extent import MapExtent, aspect_correct
        from ..kneeboard_recon.projection import Projector

        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        writer.title("Package Targets Map")
        label_font = ImageFont.truetype(
            "courbd.ttf", 13, layout_engine=ImageFont.Layout.BASIC
        )
        writer.text(
            "Orange = package targets; airfields, carriers & LHAs are named "
            "(blue = friendly, red = enemy).",
            font=label_font,
        )

        points = [(x, y) for _, x, y in self.targets]
        points += [(x, y) for x, y, *_ in self.control_points]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        margin = writer.page_margin
        top = writer.y + 8
        avail_w = writer.image_size[0] - 2 * margin
        avail_h = writer.image_size[1] - top - margin

        # World bounding box of everything shown, plus an 8% margin.
        pad = 0.08 * max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
        extent = MapExtent(
            min_x=min(xs) - pad,
            max_x=max(xs) + pad,
            min_y=min(ys) - pad,
            max_y=max(ys) + pad,
            terrain=self.terrain,
        )

        # Fill the page, and let aspect_correct grow the WORLD extent to match
        # rather than letterboxing the image. This costs the area of interest
        # nothing: the padding lands on the non-binding axis, so the scale set
        # by the binding axis is unchanged and the AO occupies exactly the
        # pixels it would have anyway -- the space that used to be blank page
        # now shows the terrain around it. The earlier letterbox was guarding
        # against SHRINKING the map to fit both axes, which is a different
        # thing and is not what this does. Flown 2026-08-17: a Syria page put
        # the whole theater in a middle band with ~390 px of dead page above
        # and below it.
        # Page-x (width) <- DCS y (east); page-y (height) <- DCS x (north).
        map_w, map_h = avail_w, avail_h
        off_x, off_y = margin, top

        # Aspect-correct first — the padded extent is what gets drawn, so it is
        # what the raster has to cover — then slide it back on if the padding
        # alone pushed it off. Both must precede the Projector below: backdrop
        # and symbology drawn for different extents is the §22 defect again.
        ao_extent = extent
        extent = align_extent_to_theater_raster(
            aspect_correct(extent, map_w, map_h), keep_visible=ao_extent
        )
        writer.image.paste(
            render_theater_basemap(extent, map_w, map_h, dark=self.dark_kneeboard),
            (off_x, off_y),
        )

        projector = Projector(extent=extent, pixel_width=map_w, pixel_height=map_h)

        def to_px(x: float, y: float) -> Tuple[int, int]:
            px, py = projector.project(DcsPoint(x, y, self.terrain))
            return off_x + px, off_y + py

        draw = writer.draw
        # Occupied boxes. Seeded with the MARKERS themselves, not just with
        # labels: markers are drawn in a pass of their own before any text, and
        # a label placed on a dot is as unreadable as one placed on a label
        # (flown 2026-08-17: a package dot printed through the middle of
        # "DOLPHIN").
        placed: List[Tuple[float, float, float, float]] = []

        def overlaps(box: Tuple[float, float, float, float]) -> bool:
            ax0, ay0, ax1, ay1 = box
            return any(
                ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1
                for bx0, by0, bx1, by1 in placed
            )

        base_labels: List[Tuple[str, int, int, Tuple[int, int, int]]] = []
        for x, y, side, kind, name in self.control_points:
            px, py = to_px(x, y)
            color = (
                self.FRIENDLY
                if side == "friendly"
                else self.ENEMY if side == "enemy" else self.NEUTRAL
            )
            if kind == "airbase":
                draw.rectangle(
                    (px - 4, py - 4, px + 4, py + 4), fill=color, outline=(0, 0, 0)
                )
            elif kind == "carrier":
                draw.polygon(
                    [(px, py - 5), (px + 5, py), (px, py + 5), (px - 5, py)],
                    fill=color,
                    outline=(0, 0, 0),
                )
            elif kind == "lha":
                draw.polygon(
                    [(px, py - 5), (px + 5, py + 4), (px - 5, py + 4)],
                    fill=color,
                    outline=(0, 0, 0),
                )
            else:
                draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=color)
                placed.append((px - 4, py - 4, px + 4, py + 4))
                continue
            placed.append((px - 6, py - 6, px + 6, py + 6))
            base_labels.append((name, px, py, color))

        label_h = 15
        right_edge = off_x + map_w
        bottom_edge = off_y + map_h - label_h

        def free_slot(px: int, py: int, tw: float) -> Optional[Tuple[float, float]]:
            """First non-overlapping label position for a marker, or None.

            Tries right of the marker then left, and within each side steps DOWN
            then UP. The old rule only stepped down and gave up at the bottom
            edge -- while still overlapping -- so it drew the label anyway and
            destroyed the one underneath as well as itself. Flown 2026-08-17:
            "DRAGONFLY"/"CRANE" and "King Abdullah II"/"Muwaffaq Salti" both
            printed on top of each other into unreadable mush, both near the
            bottom of the map.
            """
            for lx in (px + 8, px - 8 - tw):
                if lx < off_x or lx + tw > right_edge:
                    continue
                for step in (label_h, -label_h):
                    ly = py - 7
                    while (
                        off_y <= ly <= bottom_edge
                        and abs(ly - (py - 7)) <= self.MAX_LABEL_OFFSET
                    ):
                        if not overlaps((lx, ly, lx + tw, ly + label_h)):
                            return lx, ly
                        ly += step
            return None

        def leader(
            px: int, py: int, lx: float, ly: float, tw: float, color: Any
        ) -> None:
            """Join a displaced label back to the marker it belongs to.

            A label pushed clear of its dot is worse than no label: the reader
            attaches it to whatever it landed next to.

            Ends at the label's NEAR edge, and stops short of it. Drawing to the
            far edge runs the line straight through the text, which then reads as
            punctuation -- "H3 Northwest" came out as "H3-Northwest" when the
            label sat left of its marker.
            """
            near_x = lx + tw if lx + tw < px else lx
            gap = 3 if near_x < px else -3
            cx, cy = near_x + gap, ly + label_h / 2
            if math.dist((px, py), (cx, cy)) < self.LEADER_AT:
                return
            draw.line((px, py, cx, cy), fill=color, width=1)

        #: Target names already drawn. A package target that IS a control point
        #: appears in both lists, and the base pass would then print the same
        #: name a second time a few pixels away (flown: "H3 Southwest" twice).
        labelled: set[str] = set()

        target_labels: List[Tuple[str, int, int]] = []
        for name, x, y in self.targets:
            px, py = to_px(x, y)
            draw.ellipse(
                [px - 5, py - 5, px + 5, py + 5], fill=self.TARGET, outline=(0, 0, 0)
            )
            placed.append((px - 7, py - 7, px + 7, py + 7))
            target_labels.append((name, px, py))

        for name, px, py in target_labels:
            tw = label_font.getlength(name)
            slot = free_slot(px, py, tw)
            if slot is None:
                # Nowhere legible left. The marker still shows the target; an
                # overprinted name would cost this label AND its neighbour.
                continue
            lx, ly = slot
            placed.append((lx, ly, lx + tw, ly + label_h))
            labelled.add(name)
            leader(px, py, lx, ly, tw, self.TARGET)
            # White plate behind the label so it reads against the map.
            draw.rectangle(
                (lx - 1, ly, lx + tw + 1, ly + label_h), fill=(255, 255, 255)
            )
            draw.text((lx, ly), name, font=label_font, fill=(0, 0, 0))

        # Base names: a white halo instead of a solid plate, in the base's side
        # colour, so they read apart from the boxed black-on-white target labels.
        base_font = ImageFont.truetype(
            "courbd.ttf", 12, layout_engine=ImageFont.Layout.BASIC
        )
        for name, px, py, color in base_labels:
            if name in labelled:
                continue
            tw = base_font.getlength(name)
            slot = free_slot(px, py, tw)
            if slot is None:
                continue
            lx, ly = slot
            placed.append((lx, ly, lx + tw, ly + label_h))
            leader(px, py, lx, ly, tw, color)
            draw.text(
                (lx, ly),
                name,
                font=base_font,
                fill=color,
                stroke_width=2,
                stroke_fill=(255, 255, 255),
            )

        writer.write(path)
