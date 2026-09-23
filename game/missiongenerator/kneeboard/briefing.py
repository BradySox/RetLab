"""The briefing page: departure, route, arrival and the loadout line."""

import datetime
import re
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PIL import ImageFont
from suntime import Sun, SunTimeException  # type: ignore

from game.coordinates import (
    format_dms_suffix,
)
from game.data.weapons import Weapon, WeaponType
from game.radio.radios import RadioFrequency
from game.runways import RunwayData
from game.theater.bullseye import Bullseye
from game.utils import inches_hg, meters, mps, pounds
from game.weather.weather import Weather
from ..aircraft.flightdata import FlightData
from ..kneeboard_page import KneeboardPage
from ..kneeboard_recon import airport_imagery as _airport_imagery
from ..kneeboard_recon.atis import (
    THUNDERSTORM_PRESSURE_DROP_INHG,
    altimeter_setting_inhg,
    compute_qfe_inhg,
    has_thunderstorm_cells,
    wind_from_deg,
)

if TYPE_CHECKING:
    from game.theater.conflicttheater import ConflictTheater
from .flightplan import FlightPlanBuilder
from .writer import KneeboardPageWriter, LOCAL_CELL_TOKEN


def _airfield_elevation_m(
    theater: Optional["ConflictTheater"], airfield_name: str
) -> Optional[float]:
    """DCS-mesh field elevation (m) of a named airfield, or None.

    Looks up the airport via the theater's controlpoints (matched by airfield
    name) and reads ``elevation_m`` from ``resources/airport_imagery/<terrain>.json``.
    None when no theater, no matching control point, or no elevation shipped.
    Shared by the full deck's weather block and the Brief Sheet's WX line so both
    walk the same lookup chain as the recon ATIS pipeline.
    """
    if theater is None or not airfield_name:
        return None
    for cp in theater.controlpoints:
        dcs_ap = getattr(cp, "dcs_airport", None)
        if dcs_ap is None:
            continue
        if cp.full_name == airfield_name or dcs_ap.name == airfield_name:
            return _airport_imagery.field_elevation_for_airport(theater.terrain, dcs_ap)
    return None


class BriefingPage(KneeboardPage):
    """A kneeboard page containing briefing information."""

    def __init__(
        self,
        flight: FlightData,
        bullseye: Bullseye,
        weather: Weather,
        dark_kneeboard: bool,
        atis_by_name: Optional[dict[str, RadioFrequency]] = None,
        theater: Optional["ConflictTheater"] = None,
        omit_weather: bool = False,
        bluf_lines: Optional[List[str]] = None,
        zulu_tz: Optional[datetime.tzinfo] = None,
        bullseye_moved: bool = False,
        bullseye_anchor: Optional[str] = None,
        route_labels: Optional[List[str]] = None,
    ) -> None:
        self.flight = flight
        self.bullseye = bullseye
        # The cockpit's number for each route row (§102 skipped waypoints).
        self.route_labels = route_labels
        # The bullseye is pinned for the campaign, so the one turn it does move
        # is the one turn the pilots need telling.
        self.bullseye_moved = bullseye_moved
        # The control point it is planted on. A place a pilot can find on the F10
        # map beats a coordinate they have to plot; the BLUF's second BULLSEYE
        # line was struck as a duplicate, so this stays the only one.
        self.bullseye_anchor = bullseye_anchor
        self.weather = weather
        self.zulu_tz = zulu_tz
        self.dark_kneeboard = dark_kneeboard
        self.theater = theater
        self.atis_by_name = atis_by_name or {}
        # BLUF (bottom line up front): the few items a pilot needs even if this is
        # the only kneeboard page they read -- task/TOT, code words, JAM BACKUP,
        # the compact threat picture, loadout and SAR guidance. Composed by the
        # generator (``_bluf_lines``) and passed in so the page stays decoupled
        # from the threat/code-word models.
        self.bluf_lines = bluf_lines or []
        # De-duplication (design §4): drop the weather block when the recon Departure
        # page already carries it. The Friendly Packages list moved to its own page.
        self.omit_weather = omit_weather
        self.flight_plan_font = ImageFont.truetype(
            "courbd.ttf",
            16,
            layout_engine=ImageFont.Layout.BASIC,
        )

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self._render(writer)
        writer.write(path)

    def _render(self, writer: KneeboardPageWriter) -> None:
        """Draw the Mission Info page."""
        if self.flight.custom_name:
            custom_name_title = ' ("{}")'.format(self.flight.custom_name)
        else:
            custom_name_title = ""
        writer.title(f"{self.flight.callsign} Mission Info{custom_name_title}")

        # BLUF block: task/target/TOT, push + event code words, JAM BACKUP, the
        # compact threat picture, loadout and SAR guidance -- the priority items on
        # the page players open to first (design §4). Kept tight so the flight-plan
        # table still fits on this same page.
        if self.bluf_lines:
            writer.heading("BLUF")
            writer.rule()
            for line in self.bluf_lines:
                writer.text(line, wrap=True)
            writer.vspace(8)

        # TODO: Handle carriers.
        writer.heading("Airfield Info")
        writer.rule()
        # Only show the ATIS column when ATIS is in play (plugin enabled), so a
        # mission without ATIS sees no kneeboard change (design §5).
        if self.atis_by_name:
            writer.table(
                [
                    self._row_with_atis("Departure", self.flight.departure),
                    self._row_with_atis("Arrival", self.flight.arrival),
                    self._row_with_atis("Divert", self.flight.divert),
                ],
                headers=["", "Airbase", "ATC", "TCN", "I(C)LS", "RWY", "ATIS"],
            )
        else:
            writer.table(
                [
                    self.airfield_info_row("Departure", self.flight.departure),
                    self.airfield_info_row("Arrival", self.flight.arrival),
                    self.airfield_info_row("Divert", self.flight.divert),
                ],
                headers=["", "Airbase", "ATC", "TCN", "I(C)LS", "RWY"],
            )

        writer.heading(
            f"Flight Plan ({self.flight.squadron.aircraft.variant_id} - "
            f"{self.flight.task_display_name})"
        )
        writer.rule()

        units = self.flight.aircraft_type.kneeboard_units

        flight_plan_builder = FlightPlanBuilder(
            units,
            patrol_speed=self.flight.patrol_speed,
            zulu_tz=self.zulu_tz,
        )
        labels = self.route_labels or [
            str(num) for num in range(len(self.flight.waypoints))
        ]
        for label, waypoint in zip(labels, self.flight.waypoints):
            flight_plan_builder.add_waypoint(label, waypoint)

        # The fuel ladder rides in the flight plan: a Fuel column (planned remaining
        # at each RTB steerpoint) + a one-line RTB margin call-out, instead of a
        # separate near-empty Fuel Ladder page.
        # Nine columns sit 12 px inside the page at the worst case (a "10-13"
        # target block, a 25-char action, a supersonic leg, a Zulu+local time);
        # tabulate pads every header by two, so the short GS / M / Dep headers are
        # what pays for the Mach column. Pinned by test_flightplan_table_width.
        headers = ["#", "Action", "Alt", "Dist", "GS", "M", "Time", "Dep", "Fuel"]
        uom_row = [
            "",
            "",
            units.distance_short_uom,
            units.distance_long_uom,
            units.speed_uom,
            "Mach",
            "",
            "",
            units.mass_uom,
        ]

        # Colour the local figure apart from the Zulu one leading it. Zulu keeps
        # the page's own foreground -- it is what the DED reads, so the darkest
        # ink on the page is the figure being checked against the cockpit.
        # Nothing to colour on a local-only card.
        writer.table(
            flight_plan_builder.build() + [uom_row],
            headers=headers,
            font=self.flight_plan_font,
            highlight=LOCAL_CELL_TOKEN if self.zulu_tz is not None else None,
            highlight_fill=writer.col_nav,
        )

        margin_line = flight_plan_builder.fuel_margin_line()
        if margin_line is not None:
            # Amber when short — caution colour, so a fuel problem reads at a glance.
            surplus = margin_line.startswith("RTB margin +")
            writer.text(
                margin_line,
                wrap=True,
                fill=None if surplus else writer.col_caution,
            )

        tanker_line = flight_plan_builder.tanker_line()
        if tanker_line is not None:
            writer.text(tanker_line, wrap=True, fill=writer.col_caution)

        endurance_line = flight_plan_builder.patrol_endurance_line()
        if endurance_line is not None:
            writer.text(
                endurance_line,
                wrap=True,
                fill=(
                    writer.col_caution
                    if flight_plan_builder.patrol_endurance_is_short
                    else None
                ),
            )

        writer.text(self._bullseye_line())

        fl = self.flight

        # Weather block. Dropped (design §4) when the recon Departure page already
        # carries the field weather + winds + sunrise/sunset, so it isn't printed twice.
        if not self.omit_weather:
            # QNH = the temperature-corrected altimeter setting at the departure field
            # (what ATIS broadcasts), via game.utils for canonical unit conversions.
            qnh = inches_hg(self._effective_qnh_inhg())
            qnh_in_hg = f"{qnh.inches_hg:.2f}"
            qnh_hpa = f"{qnh.hecto_pascals:.0f}"
            temp_c = round(self.weather.atmospheric.temperature_celsius)
            temp_f = round(self.weather.atmospheric.temperature_celsius * 9 / 5 + 32)
            writer.text(f"Temperature: {temp_f} °F ({temp_c} °C) at sea level")
            writer.text(f"QNH: {qnh_in_hg} inHg ({qnh_hpa} hPa)")
            qfe_line = self._format_departure_qfe()
            if qfe_line is not None:
                writer.text(qfe_line)
            writer.text(
                f"Turbulence: {round(self.weather.atmospheric.turbulence_per_10cm)} per 10cm at ground level."
            )
            writer.text(
                f"Wind: {wind_from_deg(self.weather.wind.at_0m.direction)}°"
                f" / {round(mps(self.weather.wind.at_0m.speed).knots)}kts (0ft)"
                f" ; {wind_from_deg(self.weather.wind.at_2000m.direction)}°"
                f" / {round(mps(self.weather.wind.at_2000m.speed).knots)}kts (~6500ft)"
                f" ; {wind_from_deg(self.weather.wind.at_8000m.direction)}°"
                f" / {round(mps(self.weather.wind.at_8000m.speed).knots)}kts (~26000ft)"
            )
            c = self.weather.clouds
            writer.text(
                f'Cloud base: {f"{int(round(meters(c.base).feet, -2))}ft" if c else "CAVOK"}'
                f'{f", {c.preset.ui_name[:-2]}" if c and c.preset else ""}'
            )

            start_pos = fl.waypoints[0].position.latlng()
            sun = Sun(start_pos.lat, start_pos.lng)
            date = fl.squadron.coalition.game.date
            dt = datetime.datetime(date.year, date.month, date.day)
            tz = fl.squadron.coalition.game.theater.timezone
            # Get today's sunrise and sunset in UTC
            try:
                rise_utc = sun.get_sunrise_time(dt)
                rise = rise_utc + tz.utcoffset(sun.get_sunrise_time(dt))
            except SunTimeException:
                rise_utc = None
                rise = None
            try:
                set_utc = sun.get_sunset_time(dt)
                sunset = set_utc + tz.utcoffset(sun.get_sunset_time(dt))
            except SunTimeException:
                set_utc = None
                sunset = None
            writer.text(
                f"Sunrise - Sunset: {rise.strftime('%H:%M') if rise else 'N/A'} - {sunset.strftime('%H:%M') if sunset else 'N/A'}"
                f" ({rise_utc.strftime('%H:%M') if rise_utc else 'N/A'} - {set_utc.strftime('%H:%M') if set_utc else 'N/A'} UTC)"
            )

        if fl.bingo_fuel and fl.joker_fuel:
            writer.table(
                [
                    [
                        f"{units.mass(pounds(fl.bingo_fuel)):.0f} {units.mass_uom}",
                        f"{units.mass(pounds(fl.joker_fuel)):.0f} {units.mass_uom}",
                    ]
                ],
                ["Bingo", "Joker"],
            )

        if any(self.flight.laser_codes):
            codes: list[list[str]] = []
            for idx, code in enumerate(self.flight.laser_codes, start=1):
                codes.append([str(idx), "" if code is None else str(code)])
            writer.table(codes, ["#", "Laser Code"])

    def _departure_elevation_m(self) -> Optional[float]:
        """DCS-mesh field elevation (m) of the departure field, or None."""
        return _airfield_elevation_m(self.theater, self.flight.departure.airfield_name)

    def _altimeter_setting_inhg(self, elevation_m: Optional[float]) -> float:
        """Temperature-corrected altimeter-setting QNH (what ATIS reports) for a
        known field elevation; raw sea-level QNH when the elevation is unknown.
        """
        qnh_inhg = self.weather.atmospheric.qnh.inches_hg
        if elevation_m is None:
            return qnh_inhg
        return altimeter_setting_inhg(
            qnh_inhg, elevation_m, self.weather.atmospheric.temperature_celsius
        )

    def _effective_qnh_inhg(self) -> float:
        """QNH as ATIS reports it at the departure field (raw when no elevation)."""
        return self._altimeter_setting_inhg(self._departure_elevation_m())

    def _format_departure_qfe(self) -> Optional[str]:
        """Return "QFE: ..." line for the departure field, or None.

        QFE is derived from the temperature-corrected altimeter-setting QNH, so it
        equals the actual field pressure (matching the in-sim ATIS QFE).
        """
        dep = self.flight.departure
        elevation_m = self._departure_elevation_m()
        if elevation_m is None:
            return None

        # One elevation lookup feeds both the QNH correction and the QFE.
        qnh_inhg = self._altimeter_setting_inhg(elevation_m)
        qfe_inhg = compute_qfe_inhg(qnh_inhg, elevation_m)
        qfe_hpa = inches_hg(qfe_inhg).hecto_pascals
        elev_ft = meters(elevation_m).feet
        line = (
            f"QFE ({dep.airfield_name}, field elev {elev_ft:.0f} ft): "
            f"{qfe_inhg:.2f} inHg / {qfe_hpa:.1f} hPa"
        )
        if has_thunderstorm_cells(self.weather.clouds):
            qfe_low = compute_qfe_inhg(
                qnh_inhg - THUNDERSTORM_PRESSURE_DROP_INHG, elevation_m
            )
            line += (
                f" (~{qfe_low:.2f} in CB cells â€” local QNH may drop "
                "~3 mb inside storm cores)"
            )
        return line

    def airfield_info_row(
        self, row_title: str, runway: Optional[RunwayData]
    ) -> List[str]:
        """Creates a table row for a given airfield.

        Args:
            row_title: Purpose of the airfield. e.g. "Departure", "Arrival" or
                "Divert".
            runway: The runway described by this row.

        Returns:
            A list of strings to be used as a row of the airfield table.
        """
        if runway is None:
            return [row_title, "", "", "", "", ""]

        atc = ""
        if runway.atc is not None:
            atc = self.format_frequency(runway.atc)
        if runway.tacan is None:
            tacan = ""
        else:
            tacan = str(runway.tacan)
        if runway.ils is not None:
            ils = str(runway.ils)
        elif runway.icls is not None:
            ils = str(runway.icls)
        else:
            ils = ""
        return [
            row_title,
            "\n".join(textwrap.wrap(runway.airfield_name, width=17)),
            atc,
            tacan,
            ils,
            runway.runway_name,
        ]

    def _bullseye_line(self) -> str:
        """The one bullseye line: the place, its coordinates, and any move.

        The BLUF's second BULLSEYE line was struck as a duplicate, so everything
        the pilot gets about the bullseye is on this row.
        """
        where = f"{self.bullseye_anchor} — " if self.bullseye_anchor else ""
        moved = "   ** MOVED THIS TURN **" if self.bullseye_moved else ""
        coords = format_dms_suffix(self.bullseye.position.latlng())
        return f"Bullseye: {where}{coords}{moved}"

    def _row_with_atis(self, row_title: str, runway: Optional[RunwayData]) -> List[str]:
        row = self.airfield_info_row(row_title, runway)
        atis = ""
        if runway is not None:
            freq = self.atis_by_name.get(runway.airfield_name)
            if freq is not None:
                atis = self.format_frequency(freq)
        row.append(atis)
        return row

    def format_frequency(self, frequency: RadioFrequency) -> str:
        channels = self.flight.channels_for(frequency)
        if not channels:
            return str(frequency)

        names = " / ".join(
            self.flight.aircraft_type.channel_name(c.radio_id, c.channel)
            for c in channels
        )
        return f"{names}\n{frequency}"


#: A rack-mounted store names its own count ("2xMk 82", "4 x GBU-12").
_RACK_MULTIPLIER_RE = re.compile(r"^(\d+)\s*x\s*(.+)$", re.IGNORECASE)


def _brief_loadout(units: List[Any]) -> str:
    """One-line **ordnance** summary from the lead aircraft's generated pylons.

    Keeps the munitions a pilot briefs (bombs, missiles, rockets); a targeting pod
    collapses to a single "TGP" and fuel tanks to "bag". Skips the noise -- ECM pods,
    empty/clean stations, and clsids that don't resolve to a named weapon. Counts by
    station and strips a rack multiplier from the name ("2xGBU-12" -> "GBU-12").
    """
    if not units:
        return ""
    pylons = getattr(units[0], "pylons", None) or {}
    counts: Dict[str, int] = {}
    order: List[str] = []
    has_tgp = False
    has_hts = False
    for station in pylons.values():
        clsid = station.get("CLSID") if isinstance(station, dict) else None
        if not clsid:
            continue
        weapon = Weapon.with_clsid(clsid)
        if weapon is None:
            continue
        if getattr(weapon.weapon_group, "type", None) is WeaponType.TGP:
            has_tgp = True
            continue
        # A weapon whose GROUP is unnamed still has a name of its own, and the
        # group's placeholder is the literal string "Unknown" -- truthy, so it
        # won the `or` and was then dropped by the guard below. That silently
        # ate every 370 gal fuel tank on an F-16 BAI card.
        group_name = getattr(weapon.weapon_group, "name", None)
        if not group_name or group_name == "Unknown":
            group_name = weapon.name
        name = (group_name or "").strip()
        low = name.lower()
        if "harm targeting" in low:  # AN/ASQ-213 HTS pod -- a SEAD sensor, not a weapon
            has_hts = True
            continue
        if (
            not name
            or name == "Unknown"
            or "clean" in low
            or "pylon" in low
            or "ecm" in low
            or "jammer" in low
        ):
            continue
        # A rack carries several stores on one station, and the count is the
        # thing a pilot briefs: a TER with 2 x Mk-82 is two bombs, not one.
        # The multiplier used to be stripped off the name and discarded.
        per_station = 1
        if "fuel" in low or "tank" in low:
            name = "bag"
        else:
            rack = _RACK_MULTIPLIER_RE.match(name)
            if rack:
                per_station = int(rack.group(1))
                name = rack.group(2).strip()
        if name not in counts:
            order.append(name)
        counts[name] = counts.get(name, 0) + per_station
    parts = [(f"{counts[n]}× {n}" if counts[n] > 1 else n) for n in order]
    if has_hts:
        parts.append("HTS")
    if has_tgp:
        parts.append("TGP")
    return " · ".join(parts)
