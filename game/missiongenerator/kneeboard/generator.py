"""Builds and writes the kneeboard deck for every client flight."""

import datetime
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING, Tuple

from dcs.mission import Mission

from game.ato.codewords import PushCategory, present_categories, push_category_for
from game.ato.flighttype import FlightType
from game.coordinates import (
    coordinate_format,
)
from game.dcs.aircrafttype import AircraftType
from game.settings.settings import TargetIntelPrecision
from game.sitrep import Sitrep, sitrep_for_kneeboard
from game.theater import TheaterGroundObject
from ..aircraft.flightdata import FlightData
from ..csarbeacon import sar_beacon_brief
from ..briefinggenerator import MissionInfoGenerator
from ..kneeboard_page import KneeboardPage
from ..kneeboard_recon import generate_recon_pages
from ..kneeboard_recon.pages import (
    _FLIGHT_TYPES_WITH_RECON,
    _should_emit_departure,
)
from ..dtc.savedpoints import kneeboard_numbers, route_numbers
from ...persistency import kneeboards_dir

if TYPE_CHECKING:
    from game import Game
    from game.customkneeboard import CustomKneeboard
from .briefing import BriefingPage, _brief_loadout
from .support import (
    CodeWordsBlock,
    FriendlyPackagesPage,
    SupportPage,
    build_airfield_directory_rows,
)
from .pages import KneeboardIndexPage, NotesPage, SavedPointsPage, SitrepPage
from .packagesmap import PackagesMapPage, _abbreviated_target_name
from .taskpages import SeadTaskPage, StrikeTaskPage
from .threatintel import (
    ThreatCard,
    ThreatIntelBriefPage,
    _brief_sam_threats,
    build_threat_intel_cards,
)
from .writer import (
    _format_clock,
    _zulu_text,
    format_kneeboard_time,
    format_kneeboard_time_inline,
)


class KneeboardGenerator(MissionInfoGenerator):
    """Creates kneeboard pages for each client flight in the mission."""

    #: Tasks shown with a patrol window (start - end) instead of a single TOT.
    PATROL_TASKS = frozenset(
        {
            FlightType.BARCAP,
            FlightType.TARCAP,
            FlightType.REFUELING,
            FlightType.AEWC,
        }
    )

    def __init__(self, mission: Mission, game: "Game") -> None:
        super().__init__(mission, game)
        self.dark_kneeboard = self.game.settings.generate_dark_kneeboard and (
            self.mission.start_time.hour > 19 or self.mission.start_time.hour < 7
        )

    def generate(self) -> None:
        """Generates a kneeboard per client flight, grouped by airframe.

        DCS scopes kneeboards per airframe, so all client flights of a type share one
        stacked deck. Each flight's pages stay a contiguous block in deterministic
        (callsign-sorted) order; when 2+ flights share a type a one-page index is
        prepended so a pilot can flip straight to their own block (#P4).
        """
        temp_dir = Path("kneeboards")
        temp_dir.mkdir(exist_ok=True)
        for aircraft, flights in self.client_flights_by_airframe().items():
            aircraft_dir = temp_dir / aircraft.dcs_unit_type.id
            aircraft_dir.mkdir(exist_ok=True)
            # Per-flight concrete pages. paginate() may expand a flight's pages into
            # continuation pages, so flatten each flight's block before numbering.
            flight_blocks: List[Tuple[FlightData, List[KneeboardPage]]] = []
            for flight in flights:
                package_flights = [
                    f
                    for f in self.flights
                    if f.package is flight.package and f is not flight
                ]
                pages = self.generate_flight_kneeboard(flight, package_flights)
                concrete = [c for page in pages for c in page.paginate()]
                flight_blocks.append((flight, concrete))

            # When 2+ client flights share this airframe, front the stacked deck
            # with a callsign -> start-page index (§27); a lone flight's deck
            # opens straight on its Mission Info page, like stock.
            ordered_pages: List[KneeboardPage] = []
            if len(flight_blocks) > 1:
                ordered_pages.append(self._build_index_page(aircraft, flight_blocks))
            for _flight, concrete in flight_blocks:
                ordered_pages.extend(concrete)

            for idx, page in enumerate(ordered_pages):
                # The suffix picks the encoder: photographic recon basemaps go
                # out as JPEG, line-art pages stay PNG (see KneeboardPage).
                page_path = aircraft_dir / f"page{idx:02}{page.image_suffix}"
                page.write(page_path)
                self.mission.add_aircraft_kneeboard(aircraft.dcs_unit_type, page_path)
        for type in kneeboards_dir().iterdir():
            if type.is_dir():
                for kneeboard in type.iterdir():
                    self.mission.custom_kneeboards[type.name].append(kneeboard)
            else:
                self.mission.custom_kneeboards[""].append(type)

        # Player-imported custom kneeboards stored in the campaign save (see
        # game/customkneeboard.py). ``getattr`` default keeps pre-feature saves
        # working even if the __setstate__ migration hasn't run yet.
        self._inject_custom_kneeboards(
            getattr(self.game, "custom_kneeboards", []), temp_dir
        )

    def _inject_custom_kneeboards(
        self, custom_kneeboards: List["CustomKneeboard"], temp_dir: Path
    ) -> None:
        """Write each saved custom kneeboard to a temp PNG and register it.

        Bytes are written and appended like the loose-folder kneeboards: the ""
        key scopes to all client flights, an airframe id scopes to that type only
        (the finest grain DCS allows). Extracted from ``generate`` so the
        scope-routing is unit-testable without a full mission.
        """
        if not custom_kneeboards:
            return
        custom_dir = temp_dir / "_custom"
        custom_dir.mkdir(exist_ok=True)
        for idx, custom in enumerate(custom_kneeboards):
            image_path = custom_dir / f"custom{idx:02}.png"
            image_path.write_bytes(custom.image)
            key = custom.airframe_id or ""
            self.mission.custom_kneeboards[key].append(image_path)

    def client_flights_by_airframe(self) -> Dict[AircraftType, List[FlightData]]:
        """Client flights grouped by airframe, in deterministic per-airframe order.

        Only client flights are included. DCS does not support group-specific kneeboard
        pages, so every flight of a type shares the same stacked deck; sorting by
        callsign keeps the stack (and the index that fronts it) stable across
        regenerations.
        """
        by_airframe: Dict[AircraftType, List[FlightData]] = defaultdict(list)
        for flight in self.flights:
            if not flight.client_units:
                continue
            by_airframe[flight.aircraft_type].append(flight)
        for grouped in by_airframe.values():
            grouped.sort(key=lambda f: f.callsign)
        return by_airframe

    def _build_index_page(
        self,
        aircraft: AircraftType,
        flight_blocks: List[Tuple[FlightData, List[KneeboardPage]]],
    ) -> KneeboardPage:
        """The flight index fronting a stacked multi-flight airframe deck (§27).

        The index is page 1, so the first flight's block starts on page 2. Only
        called when 2+ client flights share the airframe.
        """
        rows: List[List[str]] = []
        page_cursor = 2  # this index is page 1
        for flight, concrete in flight_blocks:
            name = flight.callsign
            if flight.custom_name:
                name += f' ("{flight.custom_name}")'
            rows.append([name, flight.task_display_name, str(page_cursor)])
            page_cursor += len(concrete)
        return KneeboardIndexPage(aircraft, rows, self.dark_kneeboard)

    def _briefing_sitrep(self) -> Optional[Sitrep]:
        """The SITREP to show on the briefing page, gated by the setting + non-empty
        (§29): None on turn 1, after a quiet turn, or when the toggle is off."""
        return sitrep_for_kneeboard(
            getattr(self.game, "last_sitrep", None),
            self.game.settings.generate_sitrep_kneeboard,
        )

    def generate_task_page(self, flight: FlightData) -> Optional[KneeboardPage]:
        if flight.flight_type in (FlightType.DEAD, FlightType.SEAD):
            return SeadTaskPage(
                flight,
                self.game.coalition_for(flight.friendly).bullseye,
                self.dark_kneeboard,
            )
        elif flight.flight_type is FlightType.STRIKE:
            return StrikeTaskPage(flight, self.dark_kneeboard)
        return None

    def generate_flight_kneeboard(
        self, flight: FlightData, package_flights: List[FlightData]
    ) -> List[KneeboardPage]:
        """Returns a list of kneeboard pages for the given flight."""

        # An airframe whose avionics run Zulu gets both times on every page, so
        # the card serves the cockpit and a package coordinating in local time.
        zulu_tz = (
            self.game.theater.timezone if flight.aircraft_type.utc_kneeboard else None
        )

        airfield_rows = (
            build_airfield_directory_rows(self.game, flight, self.atis_by_name)
            if self.atis_by_name
            else []
        )

        # De-duplication (design §4): drop blocks from the always-on Mission Info page
        # when an enabled optional page already carries the same data, so nothing is
        # printed twice. Each is conditional on the *other* page existing, so a deck
        # with options off is unchanged.
        recon_on = self.game.settings.generate_target_recon_kneeboard
        # The recon Departure page carries the field weather + winds + sunrise/sunset.
        omit_weather = recon_on and _should_emit_departure(flight, self.game)

        # Threat cards are computed once and feed the BLUF's condensed SAM line on
        # the Mission Info page and (when enabled) the dedicated Threat Intel
        # Brief. Computed unconditionally so the BLUF threat picture is present
        # even when the full brief page is off.
        threat_cards, unidentified = build_threat_intel_cards(self.game, flight)
        bluf_lines = self._bluf_lines(flight, threat_cards)

        support_comms = list(self.comms)

        pages: List[KneeboardPage] = [
            BriefingPage(
                flight,
                self.game.coalition_for(flight.friendly).bullseye,
                self.game.conditions.weather,
                self.dark_kneeboard,
                atis_by_name=self.atis_by_name,
                theater=self.game.theater,
                omit_weather=omit_weather,
                bluf_lines=bluf_lines,
                route_labels=route_numbers(flight, self.game.settings),
                zulu_tz=zulu_tz,
                bullseye_moved=(
                    self.game.coalition_for(flight.friendly).bullseye_moved_on_turn
                    == self.game.turn
                ),
                bullseye_anchor=self.game.coalition_for(
                    flight.friendly
                ).bullseye_anchor_name,
            ),
            SupportPage(
                flight,
                package_flights,
                support_comms,
                self.awacs,
                self.tankers,
                self.jtacs,
                self.dark_kneeboard,
                airfield_rows=airfield_rows,
                code_words=self._code_words_block(flight),
                zulu_tz=zulu_tz,
            ),
        ]

        # Previous turn's campaign SITREP (§29) on its own page: a busy turn's
        # POW/MIA list clipped at the Mission Info page edge (flown 2026-07-19).
        # Absent on turn 1 / a quiet turn / when the toggle is off.
        if (sitrep := self._briefing_sitrep()) is not None:
            pages.append(SitrepPage(sitrep, self.dark_kneeboard))

        # Only create the notes page if there are notes to show.
        if notes := self.game.notes:
            pages.append(NotesPage(notes, self.dark_kneeboard))

        if flight.saved_points or flight.saved_drawings:
            pages.extend(
                SavedPointsPage.split(
                    flight.callsign,
                    flight.saved_points,
                    self.game.theater,
                    coordinate_format(self.game.settings),
                    self.dark_kneeboard,
                    numbers=kneeboard_numbers(flight, self.game.settings),
                    drawings=flight.saved_drawings,
                )
            )

        # The SEAD/Strike Target Info page is superseded by the recon Detail page, which
        # already lists the same emitters + role + HARM ALIC over a satellite view. When
        # that detail page will be generated for this target, drop the standalone task
        # page -- but keep it in APPROXIMATE intel (the recon page shows exact coords,
        # while the task page intentionally fuzzes them; §5), so we only fold in EXACT.
        target = getattr(flight.package, "target", None)
        recon_detail_covers_target = (
            recon_on
            and flight.flight_type in _FLIGHT_TYPES_WITH_RECON
            and isinstance(target, TheaterGroundObject)
        )
        exact_intel = (
            self.game.settings.target_intel_precision is TargetIntelPrecision.EXACT
        )
        target_page = self.generate_task_page(flight)
        folds_into_recon = (
            recon_detail_covers_target
            and exact_intel
            and flight.flight_type
            in (FlightType.SEAD, FlightType.DEAD, FlightType.STRIKE)
        )
        if target_page is not None and not folds_into_recon:
            pages.append(target_page)

        # Enemy air-defense dossier (per-system cards, recon-fog aware), gated by
        # setting. Reuses the cards already built for the BLUF; only appended when
        # there are enemy air defenses to brief.
        if self.game.settings.generate_threat_intel_kneeboard and threat_cards:
            pages.append(
                ThreatIntelBriefPage(
                    flight, threat_cards, unidentified, self.dark_kneeboard
                )
            )

        # Recon overview + detail + airfield-departure pages (gated by settings).
        if self.game.settings.generate_target_recon_kneeboard:
            pages.extend(
                generate_recon_pages(
                    flight=flight,
                    game=self.game,
                    weather=self.game.conditions.weather,
                    dark=self.dark_kneeboard,
                )
            )

        # Friendly packages: a dedicated list page (de-duped from the Mission Info
        # page, where it used to fold + spill) plus the targets map, gated by settings.
        if self.game.settings.generate_all_packages_kneeboard:
            package_rows = self.build_all_packages_rows(flight)
            if package_rows:
                pages.append(
                    FriendlyPackagesPage(flight, package_rows, self.dark_kneeboard)
                )
            pages.extend(self.generate_packages_map_page(flight))

        return pages

    def _bluf_lines(
        self, flight: FlightData, threat_cards: List[ThreatCard]
    ) -> List[str]:
        """Compose the BLUF lines for the Mission Info page (priority on page one).

        The task line is always present (task, plus target/TOT when applicable);
        the push line is gated on the code-words feature.
        The threat, loadout and SAR lines carry the survivors of the retired
        one-page Brief Sheet: a compact air + SAM threat picture, a one-line
        ordnance summary, and the SAR assets + if-down drill.
        """
        lines: List[str] = []

        # Task / target / TOT.
        parts = [flight.task_display_name]
        target = getattr(flight.package, "target", None)
        target_name = getattr(target, "name", None)
        if target_name:
            parts.append(_abbreviated_target_name(target_name)[:40])
        task_line = "TASK  " + "  —  ".join(parts)
        tot = getattr(flight.package, "time_over_target", None)
        zulu_tz = self._zulu_tz(flight)
        if tot is not None and tot != datetime.datetime.min:
            task_line += f"   TOT {format_kneeboard_time_inline(tot, zulu_tz)}"
        lines.append(task_line)

        # Push + event code words (gated by the feature toggle).
        if self.game.settings.enable_package_code_words:
            code_words = self.game.coalition_for(flight.friendly).code_words
            bits: List[str] = []
            push = code_words.push_for(flight.flight_type)
            if push:
                bits.append(f"PUSH {push}")
            bits.append(f"SUCCESS {code_words.success}")
            bits.append(f"ABORT {code_words.abort}")
            lines.append("   ".join(bits))

        # Compact threat picture: the enemy's likely CAP fighters + the condensed
        # top live SAM systems ("SA-5 S-200 138nm · SA-11 Buk 27nm · ...").
        air = self._brief_air_threats(flight)
        if air:
            lines.append(f"THREATS  AIR {air}")
        sam = _brief_sam_threats(threat_cards)
        if sam:
            lines.append(f"         SAM {sam}")

        # Known enemy GPS-denial areas (§85). Recon-fogged like every other intel
        # leaf: an un-scouted jammer is NOT briefed, so the first sign of it is a
        # pass that goes long -- finding it is worth a recon sortie.
        gps = self._brief_gps_jamming(flight)
        if gps:
            lines.append(f"         GPS {gps}")

        # One-line ordnance summary from the lead jet's generated pylons.
        loadout = _brief_loadout(flight.units)
        if loadout:
            lines.append(f"LOADOUT  {loadout}")

        # Rescue assets on this mission + the if-down drill.
        # The survivor beacon channel leads, because it is the one thing the crew
        # must dial in BEFORE they need it: an ejected pilot's radio keys this
        # frequency automatically, and every rescue airframe homes it on ADF
        # (C-130J ADF-462, UH-1H ARN-83, Mi-8 ARK-9). See csarbeacon.py.
        sar_bits = " · ".join(
            [sar_beacon_brief()]
            + [f"{role} {airframe}" for role, airframe in self._brief_sar(flight)]
        )
        if_down = (
            "If down: your beacon keys automatically — squawk 7700, voice on "
            "GUARD, stay put and stay hidden. Rescue homes the beacon; you go "
            "MIA if nobody reaches you in time"
        )
        lines.append(f"SAR      {sar_bits} — {if_down}")

        return lines

    def _code_words_block(self, flight: FlightData) -> Optional[CodeWordsBlock]:
        """The code-words block for the Support Info page, or None when the
        feature is off: one push word per task category present in the ATO (the
        flight's own marked), plus the event words (STOP JAM only with an EW
        package). The planners see the same words on the ATO package tooltip and
        the join waypoint; this is the in-cockpit copy.
        """
        if not self.game.settings.enable_package_code_words:
            return None
        coalition = self.game.coalition_for(flight.friendly)
        code_words = coalition.code_words
        own = push_category_for(flight.flight_type)
        present = present_categories(
            p.primary_task for p in coalition.ato.packages if p.primary_task is not None
        )
        if own is not None:
            present = present | {own}
        pushes = [
            (category.value, code_words.push[category], category is own)
            for category in PushCategory
            if category in present
        ]
        return CodeWordsBlock(
            theme=code_words.theme,
            pushes=pushes,
            success=code_words.success,
            abort=code_words.abort,
            stop_jam=code_words.stop_jam if PushCategory.EW in present else None,
        )

    def _brief_air_threats(self, flight: FlightData) -> str:
        """The enemy's likely CAP fighters, from the squadrons it owns."""
        try:
            opponent = self.game.coalition_for(flight.friendly).opponent
            # The faction list names types no squadron flies (test 39: Su-33 and
            # J-11A briefed against a wing of Su-27s, MiG-29s and JF-17s).
            fighters = [
                sq.aircraft
                for sq in opponent.air_wing.iter_squadrons()
                if sq.owned_aircraft > 0 and sq.aircraft.capable_of(FlightType.BARCAP)
            ]
            fighters.sort(
                key=lambda ac: ac.task_priority(FlightType.BARCAP), reverse=True
            )
            names: List[str] = []
            for aircraft in fighters:
                if aircraft.variant_id not in names:
                    names.append(aircraft.variant_id)
                if len(names) >= 2:
                    break
            if names:
                return f"{' / '.join(names)} CAP likely near the front."
        except Exception:
            pass
        return "Enemy CAP possible near the front."

    def _brief_gps_jamming(self, flight: FlightData, limit: int = 3) -> str:
        """Known enemy GPS-denial areas: 'Haina 30nm · Wittstock 45nm'.

        Empty (so the BLUF line is omitted) when the feature is off, when the
        enemy fields no jammer, or -- the interesting case -- when one exists but
        recon has not identified it yet. Fully guarded: a briefing must never fail
        to generate because an intel lookup hiccuped.
        """
        try:
            from game.retlab.gps_jamming import briefed_jammer_areas

            areas = briefed_jammer_areas(self.game, flight.friendly)
            if not areas:
                return ""
            bits = [
                f"{area.name} {area.reach.nautical_miles:.0f}nm"
                for area in areas[:limit]
            ]
            more = len(areas) - len(bits)
            if more > 0:
                bits.append(f"+{more} more")
            return (
                " · ".join(bits)
                + " — GPS weapons unreliable inside; use laser/TV or stand off."
            )
        except Exception:
            return ""

    def _brief_sar(self, flight: FlightData) -> List[Tuple[str, str]]:
        """Rescue assets on this side of the mission, as (role, aircraft type).

        The value is the aircraft type -- what to look for -- not a callsign.
        """
        rescue: List[str] = []
        for other in self.flights:
            if other.friendly is not flight.friendly:
                continue
            if other.flight_type is not FlightType.CSAR:
                continue
            airframe = other.aircraft_type.variant_id
            if airframe not in rescue:
                rescue.append(airframe)
        return [("Rescue", airframe) for airframe in rescue]

    def _zulu_tz(self, flight: FlightData) -> Optional[datetime.tzinfo]:
        """The theater zone when this airframe's card carries Zulu, else None."""
        if not flight.aircraft_type.utc_kneeboard:
            return None
        return self.game.theater.timezone

    def build_all_packages_rows(self, flight: FlightData) -> List[List[str]]:
        """One row per friendly package (target + TOT, or patrol window), sorted by time."""
        zulu_tz = self._zulu_tz(flight)
        ato = self.game.coalition_for(flight.friendly).ato
        entries: List[Tuple[datetime.datetime, List[str]]] = []
        for package in ato.packages:
            if not package.flights:
                continue
            target = (
                _abbreviated_target_name(package.target.name)[:40]
                if package.target is not None
                else ""
            )
            primary = package.primary_flight
            flight_plan = primary.flight_plan if primary is not None else None
            start = getattr(flight_plan, "patrol_start_time", None)
            end = getattr(flight_plan, "patrol_end_time", None)
            if package.primary_task in self.PATROL_TASKS and start and end:
                local = f"{_format_clock(start)} - {_format_clock(end)}"
                zulu_start = _zulu_text(start, zulu_tz)
                zulu_end = _zulu_text(end, zulu_tz)
                # Zulu leads here too, so the whole card reads one way round.
                if zulu_start and zulu_end:
                    timing = f"{zulu_start} - {zulu_end}\n{local}L"
                else:
                    timing = local
                sort_key = start
            else:
                tot = package.time_over_target
                if tot is not None and tot != datetime.datetime.min:
                    timing = format_kneeboard_time(tot, zulu_tz)
                    sort_key = tot
                else:
                    timing = ""
                    sort_key = datetime.datetime.max
            entries.append((sort_key, [package.package_description, target, timing]))

        entries.sort(key=lambda entry: entry[0])
        return [row for _, row in entries]

    def generate_packages_map_page(self, flight: FlightData) -> List[KneeboardPage]:
        """A schematic theater map labelling where each friendly package is headed."""
        player = flight.friendly
        ato = self.game.coalition_for(player).ato
        targets: List[Tuple[str, float, float]] = []
        seen: set[str] = set()
        for package in ato.packages:
            if not package.flights or package.target is None:
                continue
            # Attack packages only -- skip the support patrols (CAP, AWACS,
            # tankers) that loiter rather than head to a target. Strike, CAS,
            # DEAD/SEAD, BAI, anti-ship, OCA, air assault and recon all show.
            if package.primary_task in self.PATROL_TASKS:
                continue
            if package.target.name in seen:
                continue
            seen.add(package.target.name)
            pos = package.target.position
            targets.append(
                (_abbreviated_target_name(package.target.name)[:40], pos.x, pos.y)
            )
        if not targets:
            return []

        control_points: List[Tuple[float, float, str, str, str]] = []
        for cp in self.game.theater.controlpoints:
            if cp.captured == player:
                side = "friendly"
            elif cp.captured.is_neutral:
                side = "neutral"
            else:
                side = "enemy"
            # Fixed bases that can host aircraft get a distinct icon + name;
            # FOBs and off-map spawns stay anonymous dots to avoid clutter.
            if cp.is_carrier:
                kind = "carrier"
            elif cp.is_lha:
                kind = "lha"
            elif cp.category == "airfield":
                kind = "airbase"
            else:
                kind = "dot"
            name = cp.name[:24] if kind != "dot" else ""
            control_points.append((cp.position.x, cp.position.y, side, kind, name))

        return [
            PackagesMapPage(
                targets,
                control_points,
                self.game.theater.terrain,
                self.dark_kneeboard,
            )
        ]
