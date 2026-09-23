"""Per-task target pages for SEAD/DEAD and Strike flights."""

from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from PIL import ImageFont
from dcs.mapping import Point
from dcs.planes import F_15ESE

from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.coordinates import (
    format_dms_suffix,
)
from game.data.alic import AlicCodes
from game.missiongenerator import f15ecc
from game.settings.settings import TargetIntelPrecision
from game.theater import TheaterGroundObject, TheaterUnit
from game.theater.bullseye import Bullseye
from game.utils import meters
from ..aircraft.flightdata import FlightData
from ..kneeboard_page import KneeboardPage

from .writer import KneeboardPageWriter
from .flightplan import NumberedWaypoint


class SeadTaskPage(KneeboardPage):
    """A kneeboard page containing SEAD/DEAD target information."""

    def __init__(
        self, flight: FlightData, bullseye: Bullseye, dark_kneeboard: bool
    ) -> None:
        self.flight = flight
        self.bullseye = bullseye
        self.dark_kneeboard = dark_kneeboard

    @property
    def target_units(self) -> Iterator[TheaterUnit]:
        """The units that got a per-target waypoint, in waypoint order.

        SEAD gets a steerpoint per *emitter* and DEAD one per unit, so the two
        read different lists. This must stay the list the flight plan built from
        (game/ato/flightplans/{sead,dead}.py) or ``_target_point_numbers``
        pairing below silently prints the wrong STPT.
        """
        target = self.flight.package.target
        if not isinstance(target, TheaterGroundObject):
            return
        if self.flight.flight_type == FlightType.SEAD:
            yield from target.sead_targets
        else:
            yield from target.strike_targets

    def _target_point_numbers(self) -> List[int]:
        """STPT numbers of the per-target waypoints, in target order.

        DEAD/SEAD flights get one TARGET_POINT waypoint per target, built from
        the same ``target_units`` list (in the same order) that this page
        lists, so the i-th TARGET_POINT waypoint is the i-th listed target. The
        number is the index into the flight's waypoint list, matching the
        flight-plan page. Pairing by order (rather than by position) is robust
        to APPROXIMATE target intel offsetting the waypoint away from the unit's
        true position, which previously left every STPT blank. Old flight plans
        generated before per-target waypoints existed simply have no entries.
        """
        return [
            idx
            for idx, waypoint in enumerate(self.flight.waypoints)
            if waypoint.waypoint_type == FlightWaypointType.TARGET_POINT
        ]

    @staticmethod
    def alic_for(unit: TheaterUnit) -> str:
        try:
            return str(AlicCodes.code_for(unit))
        except KeyError:
            return ""

    def _bullseye_cue_for(self, position: Point) -> str:
        """A rough bullseye bearing/range to ``position``, accurate to ~1nm.

        Bearing is rounded to the nearest degree and range to the nearest
        nautical mile, giving the player a search anchor without exact coords.
        """
        bearing = self.bullseye.position.heading_between_point(position)
        distance = meters(self.bullseye.position.distance_to_point(position))
        return f"Bullseye {bearing:03.0f} for {distance.nautical_miles:.0f}"

    def _target_area_stpt(self) -> Optional[int]:
        """The single steerpoint that best anchors the whole site: the per-target
        waypoint nearest the site center. ``None`` when the flight has no per-target
        waypoints (e.g. legacy plans). Used for the consolidated DEAD area cue."""
        numbers = self._target_point_numbers()
        if not numbers:
            return None
        center = self.flight.package.target.position
        return min(
            numbers,
            key=lambda i: self.flight.waypoints[i].position.distance_to_point(center),
        )

    @staticmethod
    def _unit_description(unit: TheaterUnit) -> str:
        unit_type = unit.type
        return unit.name if unit_type is None else unit_type.name

    def _emitter_units(self) -> Iterator[Tuple[int, TheaterUnit]]:
        """``(index, unit)`` for the site's HARM-targetable emitters only.

        Only units with an ALIC code (radars and self-contained TELs) are HARM
        aimpoints; the launchers, command trucks and AAA guns that pad
        ``strike_targets`` aren't, and enumerating every one just hands the player the
        full site composition and exact unit counts (recon fog §3). The index pairs an
        emitter with its per-target steerpoint in the exact view, so it must index
        ``target_units`` -- the list the waypoints were built from -- not the raw
        site roster.
        """
        for index, unit in enumerate(self.target_units):
            if self.alic_for(unit):
                yield index, unit

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self.render_into(writer)
        writer.write(path)

    def render_into(self, writer: KneeboardPageWriter) -> None:
        task = "DEAD" if self.flight.flight_type == FlightType.DEAD else "SEAD"
        if self.flight.custom_name:
            custom_name_title = ' ("{}")'.format(self.flight.custom_name)
        else:
            custom_name_title = ""
        writer.title(f"{self.flight.callsign} {task} Target Info{custom_name_title}")

        # Larger-than-default fonts: this page carries only a few rows, so bigger type
        # fills the page and reads better in the cockpit. The exact-coords table
        # instead drops BELOW the default (and shortens "STPT" to "#"): at size 20
        # the longest SAM names (e.g. S-300 Big Bird SR) pushed the DMS Location
        # column off the right edge (upstream PR #766).
        body_font = ImageFont.truetype(
            "courbd.ttf", 20, layout_engine=ImageFont.Layout.BASIC
        )
        area_font = ImageFont.truetype(
            "courbd.ttf", 24, layout_engine=ImageFont.Layout.BASIC
        )
        exact_font = ImageFont.truetype(
            "courbd.ttf", 18, layout_engine=ImageFont.Layout.BASIC
        )

        target = self.flight.package.target
        if not self._target_identified and isinstance(target, TheaterGroundObject):
            # Recon fog (§3): the site is on the map as a threat (you know roughly
            # where), but it hasn't been identified -- so don't hand over its full
            # composition + HARM codes. Give the area cue + intel-tier band and prompt
            # recon, the same way the Threat Intel Brief redacts undiscovered sites.
            cue = self._bullseye_cue_for(target.position)
            writer.heading(f"{task} target area — {cue}")
            band = target.air_defense_band or "Air-defense site"
            writer.text(
                f"{band}. Composition not yet identified — engage the site to "
                "reveal the emitters and their HARM codes.",
                font=body_font,
                wrap=True,
            )
            return

        if self._use_target_area_cues:
            # Consolidated view: one bullseye cue for the *center of the site* (not
            # one per unit -- that was cluttered) plus the single target-area
            # steerpoint if one maps. The table lists only the site's HARM-targetable
            # **emitters**, deduped by type -- not every launcher, command truck and
            # gun (and not their exact counts), which would reveal the whole site.
            cue = self._bullseye_cue_for(self.flight.package.target.position)
            stpt = self._target_area_stpt()
            area = f"{task} target area"
            if stpt is not None:
                area += f" — STPT {stpt}"
            writer.heading(f"{area} — {cue}")
            seen: set[Tuple[str, str]] = set()
            rows: List[List[str]] = []
            for _, unit in self._emitter_units():
                key = (self._unit_description(unit), self.alic_for(unit))
                if key in seen:
                    continue
                seen.add(key)
                rows.append([key[0], key[1]])
            if not rows:
                # No coded emitter (e.g. a pure AAA/launcher site): fall back to the
                # full unit list so the page is never blank.
                rows = [
                    [self._unit_description(t), self.alic_for(t)]
                    for t in self.target_units
                ]
            writer.table(rows, headers=["Description", "ALIC"], font=area_font)
        else:
            # Exact (SEAD) view: per-emitter steerpoint + precise coordinates, emitters
            # only -- the launchers/trucks/guns aren't HARM aimpoints.
            target_numbers = self._target_point_numbers()
            rows = [
                self.target_info_row(
                    unit, target_numbers[i] if i < len(target_numbers) else None
                )
                for i, unit in self._emitter_units()
            ]
            if not rows:
                rows = [
                    self.target_info_row(
                        t, target_numbers[i] if i < len(target_numbers) else None
                    )
                    for i, t in enumerate(self.target_units)
                ]
            writer.table(
                rows, headers=["#", "Description", "ALIC", "Location"], font=exact_font
            )

    def target_info_row(self, unit: TheaterUnit, number: Optional[int]) -> List[str]:
        return [
            "" if number is None else str(number),
            self._unit_description(unit),
            self.alic_for(unit),
            format_dms_suffix(unit.position.latlng(), decimals=2),
        ]

    @property
    def _target_identified(self) -> bool:
        """Whether the player has discovered this site's composition (recon fog §3).

        Gates the emitter/ALIC breakdown: an un-identified site (``known_for`` False)
        is redacted to its intel-tier band so the kneeboard doesn't hand over the full
        composition before it's been recon'd. A non-TGO target (shouldn't happen for
        SEAD/DEAD) is treated as identified.
        """
        target = self.flight.package.target
        if not isinstance(target, TheaterGroundObject):
            return True
        return target.known_for(self.flight.friendly)

    @property
    def _approximate_target_intel(self) -> bool:
        return (
            self.flight.squadron.coalition.game.settings.target_intel_precision
            is TargetIntelPrecision.APPROXIMATE
        )

    @property
    def _use_target_area_cues(self) -> bool:
        return (
            self._approximate_target_intel or self.flight.flight_type == FlightType.DEAD
        )


class StrikeTaskPage(KneeboardPage):
    """A kneeboard page containing strike target information."""

    WAYPOINT_DESC_MAX_LEN = 35

    def __init__(self, flight: FlightData, dark_kneeboard: bool) -> None:
        self.flight = flight
        self.dark_kneeboard = dark_kneeboard

    @property
    def targets(self) -> Iterator[NumberedWaypoint]:
        for idx, waypoint in enumerate(self.flight.waypoints):
            if waypoint.waypoint_type == FlightWaypointType.TARGET_POINT:
                yield NumberedWaypoint(idx, waypoint)

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self.render_into(writer)
        writer.write(path)

    def render_into(self, writer: KneeboardPageWriter) -> None:
        if self.flight.custom_name:
            custom_name_title = ' ("{}")'.format(self.flight.custom_name)
        else:
            custom_name_title = ""
        writer.title(f"{self.flight.callsign} Strike Task Info{custom_name_title}")

        is_f15e = self.flight.units[0].unit_type == F_15ESE
        headers = ["STPT", "Description", "Location"]
        if self._approximate_target_intel:
            headers[2] = "Cue"
        writer.table(
            [
                [
                    str(target.number),
                    writer.wrap_line(
                        self._target_description(
                            target.waypoint.display_name, i, is_f15e
                        ),
                        self.WAYPOINT_DESC_MAX_LEN,
                    ),
                    (
                        "Search around target area waypoint"
                        if self._approximate_target_intel
                        else format_dms_suffix(
                            target.waypoint.position.latlng(), decimals=2
                        )
                    ),
                ]
                for i, target in enumerate(self.targets)
            ],
            headers=headers,
        )

    @staticmethod
    def _target_description(display_name: str, index: int, is_f15e: bool) -> str:
        """The Strike Task 'Description' cell for one target.

        Built from the waypoint's display_name so a player's rename shows here too, and
        NOT written back to the waypoint: the F15E CC mission reference stays
        confined to this page. (The previous code mutated pretty_name in place, which both
        leaked the DTC tag into the list / flight-plan kneeboard and, once renames moved to
        custom_name, regressed this page to the long auto name.)
        """
        if is_f15e:
            # Same numbering the .miz writer uses; worded as the jet's Smart Weapons page
            # shows it, where the WSO steps to it with NEXT SET / NEXT MSN.
            slot = f15ecc.cc_mission(index)
            if slot is not None:
                return f"{display_name} (CC {slot[0]}/{slot[1]})"
        return display_name

    @property
    def _approximate_target_intel(self) -> bool:
        return (
            self.flight.squadron.coalition.game.settings.target_intel_precision
            is TargetIntelPrecision.APPROXIMATE
        )
