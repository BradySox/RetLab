"""The enemy air-defense dossier: threat cards built from the player's (fogged) intel."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING, Tuple

from PIL import ImageFont
from dcs.mapping import Point

from game.data.alic import AlicCodes
from game.data.threat_reference import ThreatReference, reference_for
from game.data.units import UnitClass
from game.theater import TheaterGroundObject, TheaterUnit
from game.theater.bullseye import Bullseye
from game.theater.theatergroundobject import EwrGroundObject, SamGroundObject
from game.utils import meters
from ..aircraft.flightdata import FlightData
from ..kneeboard_page import KneeboardPage

if TYPE_CHECKING:
    from game import Game
from .writer import KneeboardPageWriter

#: Short codes for the intel-tier bands on the Threat Intel Brief, so an
#: undiscovered site can be labelled by tier ("Unidentified MERAD") without
#: leaking its exact system.
_AD_BAND_SHORT = {
    "Long-range SAM": "LORAD",
    "Medium-range SAM": "MERAD",
    "Short-range SAM": "SHORAD",
    "Point-defense SAM": "PD SAM",
    "AAA": "AAA",
    "Early-warning radar": "EWR",
}


def _threat_harm_code(tgo: TheaterGroundObject) -> Optional[int]:
    """First HARM ALIC code among the site's live units, or None if none is coded."""
    for unit in tgo.units:
        if not unit.alive:
            continue
        try:
            return AlicCodes.code_for(unit)
        except KeyError:
            continue
    return None


# Which of a SAM/EWR site's units names its threat card and supplies the curated
# reference. UNLIKE the recon-map "greatest threat" ranking (``_greatest_alive_threat``,
# which keys on the lethal *radar* to size the engagement ring), a SEAD/DEAD brief
# should name the *weapon system* the player is tied to. So launchers and track radars
# (the HARM-targetable shooters) outrank the search / acquisition / early-warning radars
# whose DCS display names read as "... SR" and would otherwise hijack the card — e.g. an
# SA-5 site labelled by its co-located ST-68U "Tin Shield SR" (and described as the
# weaponless EWR) instead of its Square Pair TR. A bare search/EW radar still names its own
# card (nothing lethal outranks it), which is honest. Lower wins.
_CARD_IDENTITY_PRIORITY: Dict[UnitClass, int] = {
    UnitClass.TRACK_RADAR: 1,  # Square Pair, Flap Lid, Low Blow, Hawk TR
    UnitClass.SEARCH_TRACK_RADAR: 1,  # Straight Flush (SA-6) — lethal & signature
    UnitClass.TELAR: 1,  # Fire Dome (SA-11), Tor, Tunguska, Osa, Roland
    UnitClass.LAUNCHER: 2,  # bare launchers (S-200, S-300 TEL, SA-2/3)
    UnitClass.MANPAD: 2,
    UnitClass.SHORAD: 2,
    UnitClass.AAA: 3,
    UnitClass.SEARCH_RADAR: 6,  # Big Bird, Snow Drift, Tin Shield, Flat Face, Dog Ear
    UnitClass.AAA_RADAR: 6,  # SON-9 Fire Can: ranks with the radars it was split from
    UnitClass.SPECIALIZED_RADAR: 6,  # Clam Shell
    UnitClass.EARLY_WARNING_RADAR: 7,  # 1L13 / 55G6 — only names a card when alone
}

_CARD_IDENTITY_DEFAULT = 5


def _system_identity(
    tgo: TheaterGroundObject,
) -> Tuple[Optional[str], Optional[ThreatReference]]:
    """Display name + curated reference identifying a site as its weapon system.

    Picks the highest-priority unit (weapon system over search/EW radar — see
    ``_CARD_IDENTITY_PRIORITY``) for the card name, and the first curated reference
    found scanning units in that same order for the stat block. Live units win ties
    over dead ones, so a partially-attrited site still names from a survivor; the name
    is otherwise stable across losses so live and dead sites of one system share a card.
    Returns ``(None, None)`` only when the site has no units at all.
    """
    units = list(tgo.units)
    if not units:
        return None, None

    def rank(unit: TheaterUnit) -> Tuple[int, int]:
        unit_type = getattr(unit, "unit_type", None)
        unit_class = getattr(unit_type, "unit_class", None)
        priority = (
            _CARD_IDENTITY_PRIORITY.get(unit_class, _CARD_IDENTITY_DEFAULT)
            if isinstance(unit_class, UnitClass)
            else _CARD_IDENTITY_DEFAULT
        )
        # Alive first within a tier (0 sorts before 1); sorted() is stable otherwise.
        return priority, 0 if getattr(unit, "alive", False) else 1

    ordered = sorted(units, key=rank)

    name: Optional[str] = None
    for unit in ordered:
        candidate = getattr(getattr(unit, "unit_type", None), "display_name", None)
        if candidate:
            name = candidate
            break
    if name is None:
        name = ordered[0].type.name

    ref: Optional[ThreatReference] = None
    for unit in ordered:
        ref = reference_for(unit.type.id)
        if ref is not None:
            break
    return name, ref


def _bullseye_brg_range(bullseye: Bullseye, position: Point) -> str:
    """Bullseye bearing/range cue ("045/30") to a position, ~1° / 1nm accuracy."""
    bearing = bullseye.position.heading_between_point(position)
    distance = meters(bullseye.position.distance_to_point(position))
    return f"{bearing:03.0f}/{distance.nautical_miles:.0f}"


@dataclass(frozen=True)
class ThreatCard:
    """One enemy air-defense *system* in the dossier (all its sites aggregated)."""

    system: str
    band: str
    identified: bool
    guidance: str
    ceiling: str
    mez_nm: str
    detect_nm: str
    harm: str
    live: int
    dead: int
    cues: List[str]
    defeat: str
    sort_range_m: float


@dataclass
class _KnownAccum:
    band: str
    live: int = 0
    dead: int = 0
    mez_m: float = 0.0
    det_m: float = 0.0
    harm: Optional[str] = None
    ref: Optional[ThreatReference] = None
    cues: List[str] = field(default_factory=list)


@dataclass
class _UnknownAccum:
    band: str
    count: int = 0
    cues: List[str] = field(default_factory=list)


def build_threat_intel_cards(
    game: "Game", flight: FlightData
) -> Tuple[List[ThreatCard], int]:
    """Per-system threat cards for the enemy air-defense laydown (recon-fog aware).

    Sites are aggregated by system: each identified system becomes one card with a
    curated stat block (guidance, ceiling, defeat note from
    ``game.data.threat_reference``) over its live numbers (MEZ, detection, HARM
    ALIC) plus the live/dead site counts and bullseye cues. Recon fog (design §3): a
    site the player has not identified (``known_for`` False) contributes only to a
    per-band "Unidentified MERAD" card — its system, ring and HARM code are withheld
    until a TARPS overflight reveals it. Cards sort live-most-lethal → unidentified.
    Returns the cards plus the count of unidentified sites (for the intro line).
    """
    player = flight.friendly
    bullseye = game.coalition_for(player).bullseye

    known: Dict[str, _KnownAccum] = {}
    unknown: Dict[str, _UnknownAccum] = {}
    unidentified = 0
    for tgo in game.theater.ground_objects:
        if not isinstance(tgo, (SamGroundObject, EwrGroundObject)):
            continue
        if tgo.is_friendly(player):
            continue
        band = tgo.air_defense_band
        short = _AD_BAND_SHORT.get(band or "", band or "AD")
        cue = _bullseye_brg_range(bullseye, tgo.position)
        if not tgo.known_for(player):
            unidentified += 1
            unknown_acc = unknown.setdefault(short, _UnknownAccum(short))
            unknown_acc.count += 1
            unknown_acc.cues.append(cue)
            continue
        name, ref = _system_identity(tgo)
        if name is None:
            name = band or "AD site"
        site = known.setdefault(name, _KnownAccum(short))
        if tgo.is_dead():
            site.dead += 1
        else:
            site.live += 1
        site.cues.append(cue)
        site.mez_m = max(site.mez_m, tgo.max_threat_range().meters)
        site.det_m = max(site.det_m, tgo.max_detection_range().meters)
        if site.harm is None:
            code = _threat_harm_code(tgo)
            site.harm = str(code) if code is not None else None
        if site.ref is None:
            site.ref = ref

    cards: List[ThreatCard] = []
    for name, site in known.items():
        ref = site.ref
        cards.append(
            ThreatCard(
                system=name,
                band=site.band,
                identified=True,
                guidance=ref.guidance if ref else "—",
                ceiling=f"{ref.ceiling_ft:,} ft" if ref and ref.ceiling_ft else "—",
                mez_nm=(
                    f"{meters(site.mez_m).nautical_miles:.0f}"
                    if site.mez_m > 0
                    else "—"
                ),
                detect_nm=(
                    f"{meters(site.det_m).nautical_miles:.0f}"
                    if site.det_m > 0
                    else "—"
                ),
                harm=site.harm or "—",
                live=site.live,
                dead=site.dead,
                cues=site.cues,
                defeat=ref.defeat if ref else "",
                sort_range_m=site.mez_m,
            )
        )
    # Live, longest-range systems first.
    cards.sort(key=lambda c: (0 if c.live else 1, -c.sort_range_m))

    unknown_cards = [
        ThreatCard(
            system=f"Unidentified {acc.band}",
            band=acc.band,
            identified=False,
            guidance="—",
            ceiling="—",
            mez_nm="—",
            detect_nm="—",
            harm="—",
            live=acc.count,
            dead=0,
            cues=acc.cues,
            defeat="",
            sort_range_m=0.0,
        )
        for acc in sorted(unknown.values(), key=lambda a: a.band)
    ]
    return cards + unknown_cards, unidentified


class ThreatIntelBriefPage(KneeboardPage):
    """Enemy air-defense dossier for the player — one card per system.

    Adapts the per-system "threat card" of professional campaign Intelligence
    Briefings to the dynamic campaign: each identified SAM/EWR system gets a card
    with a curated stat block (guidance, ceiling, **how to defeat**) over its live
    numbers (MEZ, detection, HARM ALIC), site counts and bullseye cues. Recon-fog
    aware (design §3): undiscovered sites collapse into per-band "Unidentified"
    cards until a TARPS overflight reveals them. Cards pack down the page and
    overflow onto continuation pages.
    """

    def __init__(
        self,
        flight: FlightData,
        cards: List[ThreatCard],
        unidentified: int,
        dark_kneeboard: bool,
        continued: bool = False,
    ) -> None:
        self.flight = flight
        self.cards = cards
        self.unidentified = unidentified
        self.dark_kneeboard = dark_kneeboard
        self.continued = continued

    def _title(self) -> str:
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        cont = " (cont.)" if self.continued else ""
        return f"{self.flight.callsign} Threat Intel Brief{custom}{cont}"

    def _intro(self) -> str:
        intro = "Enemy air-defense laydown. MEZ in nm; BE = bullseye bearing/range."
        if self.unidentified:
            # No total count: how many unidentified (often mobile) sites are in
            # theatre is intel we wouldn't realistically have (design §3).
            intro += " Unidentified contacts remain — engage them to ID."
        return intro

    def _heading_font(self) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(
            "courbd.ttf", 26, layout_engine=ImageFont.Layout.BASIC
        )

    def _body_font(self) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(
            "courbd.ttf", 19, layout_engine=ImageFont.Layout.BASIC
        )

    def _draw_header(self, writer: KneeboardPageWriter) -> None:
        writer.title(self._title())
        if not self.continued:
            writer.text(self._intro(), wrap=True)
        writer.vspace(4)

    @staticmethod
    def _fit_cues(
        cues: List[str],
        limit: int,
        *,
        count_overflow: bool,
        font: Optional[ImageFont.FreeTypeFont] = None,
        avail_px: Optional[float] = None,
    ) -> str:
        """Bullseye cue list truncated to a hard ``limit`` AND (when a font + width are
        given) to the pixels available on the line, so the cue string never runs off
        the right edge. Overflow shows the remaining count ("+N") when ``count_overflow``
        else an ellipsis ("…") -- an unidentified card withholds its count (design §3).
        """
        shown: List[str] = []
        for cue in cues[:limit]:
            if (
                shown
                and font is not None
                and avail_px is not None
                and font.getlength(", ".join(shown + [cue])) > avail_px
            ):
                break
            shown.append(cue)
        text = ", ".join(shown)
        remaining = len(cues) - len(shown)
        if remaining > 0:
            text += f", +{remaining}" if count_overflow else ", …"
        return text

    def _render_card(self, writer: KneeboardPageWriter, card: ThreatCard) -> None:
        body = self._body_font()
        # System name in emphasis; the same four-colour scheme as the Brief Sheet --
        # amber = the threat envelope (MEZ/Detect), blue = the HARM code + bullseye cues.
        writer.text(card.system, font=self._heading_font(), fill=writer.col_emphasis)
        writer.rule(gap_below=4)
        if card.identified:
            writer.text(
                f"Guidance: {card.guidance}    Ceiling: {card.ceiling}", font=body
            )
            writer.text_runs(
                [
                    ("MEZ ", None),
                    (f"{card.mez_nm} nm", writer.col_caution),
                    ("   Detect ", None),
                    (f"{card.detect_nm} nm", writer.col_caution),
                    ("   HARM ", None),
                    (card.harm, writer.col_nav),
                    ("   Band ", None),
                    (card.band, None),
                ],
                font=body,
            )
            sites = f"Sites: {card.live} live"
            if card.dead:
                sites += f" / {card.dead} dead"
            prefix = f"{sites}   BE "
            writer.text_runs(
                [
                    (prefix, None),
                    (
                        self._fit_cues(
                            card.cues,
                            6,
                            count_overflow=True,
                            font=body,
                            avail_px=self._cue_avail_px(writer, body, prefix),
                        ),
                        writer.col_nav,
                    ),
                ],
                font=body,
            )
            if card.defeat:
                writer.text(f"DEFEAT: {card.defeat}", font=body, wrap=True)
        else:
            # Engaging a site is the ONLY thing that reveals it since the
            # 2026-08-18 §3 rework; recon finds hidden command posts and
            # nothing else. This line briefed a TARPS sortie that cannot
            # identify any of these, and contradicted the intro above it.
            prefix = "Engage to ID.   BE "
            writer.text_runs(
                [
                    (prefix, None),
                    (
                        self._fit_cues(
                            card.cues,
                            8,
                            count_overflow=False,
                            font=body,
                            avail_px=self._cue_avail_px(writer, body, prefix),
                        ),
                        writer.col_nav,
                    ),
                ],
                font=body,
            )
        writer.vspace(16)

    @staticmethod
    def _cue_avail_px(
        writer: KneeboardPageWriter, font: ImageFont.FreeTypeFont, prefix: str
    ) -> float:
        """Pixels left on the cue line after the label prefix and a margin reserved
        for the overflow marker (", +NN" / ", …")."""
        line_left = writer.image_size[0] - writer.page_margin - writer.x
        return line_left - font.getlength(prefix) - font.getlength(", +99")

    def _card_height(self, card: ThreatCard) -> int:
        probe = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        probe.y = 0
        self._render_card(probe, card)
        return probe.y

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self._draw_header(writer)
        for card in self.cards:
            self._render_card(writer, card)
        writer.write(path)

    def paginate(self) -> List[KneeboardPage]:
        # Greedily pack cards down each page; overflow starts a continuation page
        # (header repeats, intro only on the first). Always place >=1 card per page
        # so an over-tall card can't loop.
        pages: List[KneeboardPage] = []
        remaining = self.cards
        continued = self.continued
        while remaining:
            page = ThreatIntelBriefPage(
                self.flight, [], self.unidentified, self.dark_kneeboard, continued
            )
            writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
            page._draw_header(writer)
            limit = writer.image_size[1] - writer.page_margin
            fit = 0
            for card in remaining:
                if fit and writer.y + self._card_height(card) > limit:
                    break
                self._render_card(writer, card)
                fit += 1
            pages.append(
                ThreatIntelBriefPage(
                    self.flight,
                    remaining[:fit],
                    self.unidentified,
                    self.dark_kneeboard,
                    continued,
                )
            )
            remaining = remaining[fit:]
            continued = True
        return pages or [self]


def _brief_sam_threats(cards: List[ThreatCard], limit: int = 3) -> str:
    """Condensed top live SAM/AD systems: 'SA-5 S-200 138nm · SA-10 65nm · ...'."""
    bits: List[str] = []
    for card in cards:
        if not (card.identified and card.live):
            continue
        label = card.system.split('"')[0] if '"' in card.system else card.system
        label = " ".join(label.replace("SAM ", "").split()[:3])[:16]
        suffix = f" {card.mez_nm}nm" if card.mez_nm not in ("—", "") else ""
        bits.append(f"{label}{suffix}".strip())
        if len(bits) >= limit:
            break
    return " · ".join(bits)
