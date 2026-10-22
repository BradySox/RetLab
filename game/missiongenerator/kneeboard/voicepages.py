"""Cheat sheets for the voice controllers (§116-§119): the ABCCC, SkyEye's AWACS, Vacuum, ATC.

Written for pilots new to talking to a bot on SRS: who is who, which frequency, the
exact words to say, what the answers mean, and what to do when nobody answers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from game.ato.flighttype import FlightType
from game.radio.radios import RadioFrequency
from game.retlab.voice_atc import AtcField, station_name
from ..kneeboard_page import KneeboardPage
from .writer import KneeboardPageWriter


def _freq(frequency: RadioFrequency) -> str:
    return f"{frequency.mhz:.3f} {frequency.modulation.name}"


def _spoken_freq(frequency: RadioFrequency) -> str:
    """``262.0`` or ``270.45``: a frequency as ATC says it."""
    label = f"{frequency.mhz:.3f}".rstrip("0")
    return label + "0" if label.endswith(".") else label


def _lines(writer: KneeboardPageWriter, lines: list[str]) -> None:
    for line in lines:
        writer.text(line, wrap=True)


#: The package's life, left to right, with the two side branches under it.
FLOW_STEPS = ("CHECK IN", "HOLD", "PUSH", "EGRESS", "RTB")
FLOW_BRANCHES = (
    (1, ('"Hold, hold":', "stay, max 2")),
    (2, ('"Abort":', "go home")),
)


def _flow_chart(writer: KneeboardPageWriter) -> None:
    """A row of boxes joined by arrows, with the hold and abort branches below."""
    draw, font = writer.draw, writer.content_font
    left = writer.page_margin
    width = writer.image_size[0] - 2 * writer.page_margin
    gap = 22
    box_w = (width - gap * (len(FLOW_STEPS) - 1)) // len(FLOW_STEPS)
    box_h = 44
    top = writer.y + 4
    ink = writer.foreground_fill
    for i, step in enumerate(FLOW_STEPS):
        x0 = left + i * (box_w + gap)
        draw.rectangle((x0, top, x0 + box_w, top + box_h), outline=ink, width=2)
        tw = draw.textlength(step, font=font)
        draw.text((x0 + (box_w - tw) / 2, top + 12), step, font=font, fill=ink)
        if i < len(FLOW_STEPS) - 1:
            ax, ay = x0 + box_w + 3, top + box_h / 2
            draw.line((ax, ay, ax + gap - 6, ay), fill=ink, width=2)
            draw.polygon(
                [(ax + gap - 6, ay - 5), (ax + gap - 1, ay), (ax + gap - 6, ay + 5)],
                fill=ink,
            )
    below = top + box_h + 8
    for index, label in FLOW_BRANCHES:
        x0 = left + index * (box_w + gap)
        draw.line(
            (x0 + box_w / 2, top + box_h, x0 + box_w / 2, below + 4), fill=ink, width=2
        )
        for n, line in enumerate(label):
            draw.text(
                (x0, below + 8 + n * 22), line, font=font, fill=writer.col_caution
            )
    writer.y = below + 58


class AbcccPage(KneeboardPage):
    """How to work with the ABCCC on STRIKE."""

    def __init__(
        self,
        controller: str,
        strike: RadioFrequency,
        awacs: Optional[str],
        callsign: str,
        dark_kneeboard: bool,
        fmt: Callable[[RadioFrequency], str] = _freq,
    ) -> None:
        #: How a frequency prints: with its preset channel when the generator knows it.
        self.fmt = fmt
        self.controller = controller
        self.strike = strike
        self.awacs = awacs
        self.callsign = callsign
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        w = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        c, me = self.controller, self.callsign
        w.title(f"Talking to {c} (ABCCC)")
        w.text(f"STRIKE: {self.fmt(self.strike)}", fill=w.col_nav)
        _lines(
            w,
            [
                f"{c} is a C-130 command post. It runs your package: check-in, "
                "push time, holds, aborts and egress.",
                (
                    f"{self.awacs} (AWACS) is also on STRIKE, in a different voice. "
                    "It only speaks up for threats or when you call it."
                    if self.awacs
                    else "The AWACS is not on STRIKE this mission."
                ),
                f"No {c} in the air means no package control: fly your planned times.",
            ],
        )
        w.rule()
        w.heading("The flow")
        _flow_chart(w)
        w.rule()
        w.heading("How to call")
        _lines(
            w,
            [
                "Key the radio on STRIKE. Say THEIR name, then YOUR name, then the call.",
                f'"{c}, {me}, checking in."  (or "with you", "on station")',
                f'"{c}, {me}, ready to push."',
                f'"{c}, {me}, say push time."',
                "No voice? F10 menu > Package control > Check in does the same.",
            ],
        )
        w.rule()
        w.heading("What you will hear")
        _lines(
            w,
            [
                '"Radar contact ... angels 20, push time 1432": go to your HOLD '
                "point at that altitude and wait.",
                '"... package, check in" (3 min before push): answer with your '
                f'name and "ready", e.g. "{c}, {me}, ready".',
                '"Push": leave the HOLD now for the target.',
                '"Hold, hold ... new push time": stay at the HOLD; SEAD or escort '
                "is not up yet. At most two holds.",
                '"Abort, abort, abort ... RTB": the strike is off. Go home.',
                '"All strikers egressed. RTB": job done, head home.',
            ],
        )
        w.rule()
        w.text(
            "Tip: speak at normal speed, wait for the beep to end, and use the "
            "same name as on your kneeboard.",
            fill=w.col_muted,
            wrap=True,
        )
        w.write(path)


class SkyEyeAwacsPage(KneeboardPage):
    """How to work with SkyEye's AWACS."""

    def __init__(
        self,
        awacs: str,
        frequency: RadioFrequency,
        strike: Optional[RadioFrequency],
        callsign: str,
        dark_kneeboard: bool,
        fmt: Callable[[RadioFrequency], str] = _freq,
    ) -> None:
        #: How a frequency prints: with its preset channel when the generator knows it.
        self.fmt = fmt
        self.awacs = awacs
        self.frequency = frequency
        self.strike = strike
        self.callsign = callsign
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        w = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        a, me = self.awacs, self.callsign
        w.title(f"Talking to {a} (AWACS)")
        w.text(f"{a}: {self.fmt(self.frequency)}", fill=w.col_nav)
        if self.strike is not None:
            w.text(
                f"Also on STRIKE {self.fmt(self.strike)} for threats and your calls.",
                fill=w.col_nav,
                wrap=True,
            )
        _lines(
            w,
            [
                f"{a} is a voice AWACS (SkyEye). It sees the air picture and answers "
                "when you talk to it.",
                f"Call yourself by your callsign and seat, {me}: the mission tells "
                f"{a} which jet that is.",
            ],
        )
        w.rule()
        w.heading("Calls")
        _lines(
            w,
            [
                f'"{a}, {me}, radio check."   Can it hear you?',
                f'"{a}, {me}, checking in."   (or "with you", "on station")',
                f'"{a}, {me}, picture."   Where are the bandits?',
                f'"{a}, {me}, bogey dope."   Nearest threat to you.',
                f'"{a}, {me}, declare 090 20 15 thousand."   Is that contact '
                "friendly or hostile?",
            ],
        )
        w.rule()
        w.heading("What it means")
        _lines(
            w,
            [
                '"BRAA 270/25, 20 thousand, hot": bearing 270, 25 NM, '
                "20,000 ft, flying at you.",
                '"Threat ... hostile": it thinks that group can hurt you. Act now.',
                '"Merged": the bandit is on top of you.',
                '"Clean": nothing hostile near you.',
            ],
        )
        w.rule()
        w.heading("Nobody answers?")
        _lines(
            w,
            [
                "1. Is your radio on the right frequency in the SRS overlay?",
                "2. Does the SRS radio light up when you transmit?",
                "3. Did you start with its name? It ignores calls that don't.",
                "4. Say it again, slower.",
            ],
        )
        w.write(path)


class AtcPage(KneeboardPage):
    """Voice ATC (§119): the field frequencies, the squawk and the calls in order."""

    def __init__(
        self,
        callsign: str,
        squawk: str,
        departure: Optional[AtcField],
        arrival: Optional[AtcField],
        dark_kneeboard: bool,
        divert: Optional[AtcField] = None,
        preset: Optional[Callable[[RadioFrequency], Optional[str]]] = None,
    ) -> None:
        self.callsign = callsign
        self.squawk = squawk
        self.departure = departure
        self.arrival = arrival
        self.divert = divert
        #: The preset a frequency sits on in the flight's jets ("COMM2 Ch 2"), or None.
        self.preset = preset or (lambda _: None)
        self.dark_kneeboard = dark_kneeboard

    def _station(self, name: str, frequency: RadioFrequency) -> str:
        """``Tel Nof Ground: COMM2 Ch 2, 130.600 AM``, or the frequency alone when not preset."""
        channel = self.preset(frequency)
        return f"  {name}: {channel + ', ' if channel else ''}{_freq(frequency)}"

    def _fields(self) -> list[tuple[str, AtcField]]:
        """Each field once: home, then a different arrival, then the divert."""
        out: list[tuple[str, AtcField]] = []
        for role, f in (
            ("home", self.departure),
            ("arrival", self.arrival),
            ("divert", self.divert),
        ):
            if f is not None and all(f.name != seen.name for _, seen in out):
                out.append((role, f))
        return out

    def write(self, path: Path) -> None:
        w = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        me = self.callsign
        out, home = self.departure, self.arrival or self.departure
        w.title("Talking to ATC")
        for role, f in self._fields():
            w.text(f"{f.name} ({role}), runway {f.runway}", fill=w.col_nav)
            w.text(
                self._station(station_name(f.name, "ground"), f.ground), fill=w.col_nav
            )
            w.text(
                self._station(station_name(f.name, "tower"), f.tower), fill=w.col_nav
            )
        w.text(f"Your squawk: {self.squawk}", fill=w.col_nav)
        _lines(
            w,
            [
                "Say the station, then YOUR name, then the request. Read back what "
                "ATC gives you, then your name (your name first works too).",
                '"Readback incomplete" means say the missing part again; "read '
                'back" means ATC did not hear yours.',
                "Use the runway ATC gives you: once AI traffic takes off, it is the "
                "one they use, which can differ from the planned runway.",
            ],
        )
        if out is not None:
            o = out.name
            w.rule()
            w.heading("Going out")
            _lines(
                w,
                [
                    f'"{o} Ground, {me}, request taxi."',
                    f'  ATC: "Squawk {self.squawk}, taxi to runway {out.runway}, hold '
                    f'short, contact Tower {_spoken_freq(out.tower)}."',
                    f'  You: "Squawk {self.squawk}, hold short {out.runway}, {me}."',
                    f'"{o} Tower, {me}, holding short runway {out.runway}, ready."',
                    f'  ATC: "Runway {out.runway}, wind, altimeter, cleared for takeoff."',
                    f'  You: "Cleared for takeoff {out.runway}, {me}."',
                    f'"{o} Tower, {me}, airborne."  (or "outbound")',
                ],
            )
        if home is not None:
            h = home.name
            w.rule()
            w.heading("Coming home, at 5 NM")
            _lines(
                w,
                [
                    f'"{h} Tower, {me}, 5 miles, full stop."  (or "request the overhead")',
                    f'  ATC: "Runway {home.runway}, wind, cleared to land."  You: '
                    f'"Cleared to land {home.runway}, {me}."',
                    '  Runway busy: "Enter the pattern at 3,000."',
                    f'After landing, you: "Tower, {me}, clear of the runway."  '
                    'ATC: "Taxi to parking."',
                    f'Emergency: "Mayday, {me}, emergency fuel." Land on any runway.',
                ],
            )
        w.rule()
        _lines(
            w,
            [
                "The lead talks for the flight going out. Coming home, a wingman "
                "may ask for their own landing.",
                "Moving, taking off or landing without clearance gets a radio call. "
                "Nothing stops you.",
                '"Say again" and "radio check" work on both frequencies. No voice? '
                "F10 menu > ATC makes the same calls.",
            ],
        )
        w.write(path)


#: The player tasks that get the Vacuum card (user call, 2026-10-21).
VACUUM_TASKS = frozenset({FlightType.SEAD, FlightType.SEAD_ESCORT, FlightType.DEAD})

#: The radar names Vacuum says (``game.retlab.vacuum.emitter_label``), what each is and
#: how far it reaches, roughly. A pilot's guide, not a threat table.
VACUUM_RADARS = (
    ("early warning radar", "search radar: sees you far out", "no missiles"),
    ("SA-2, SA-3", "old SAM, fixed site", "about 25, 12 NM"),
    ("SA-5", "very long-range SAM, fixed", "about 100 NM, high"),
    ("SA-6", "mobile SAM", "about 13 NM"),
    ("SA-8", "SAM on one truck", "about 6 NM, low"),
    ("SA-10", "long-range SAM", "about 40 NM: the big one"),
    ("SA-11", "mobile SAM", "about 19 NM"),
    ("SA-15, SA-19", "short-range SAM", "about 6 NM, low"),
    ("Hawk, Patriot", "western SAM, if red has one", "about 25, 40 NM"),
)


class VacuumPage(KneeboardPage):
    """Talking to Vacuum (§118): for SEAD, SEAD Escort and DEAD players when one flies."""

    def __init__(
        self,
        frequency: RadioFrequency,
        strike: Optional[RadioFrequency],
        callsign: str,
        dark_kneeboard: bool,
        fmt: Callable[[RadioFrequency], str] = _freq,
        casual: bool = False,
    ) -> None:
        #: How a frequency prints: with its preset channel when the generator knows it.
        self.fmt = fmt
        self.frequency = frequency
        self.strike = strike
        self.callsign = callsign
        self.dark_kneeboard = dark_kneeboard
        self.casual = casual

    def write(self, path: Path) -> None:
        w = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        me = self.callsign
        w.title("Talking to Vacuum (ELINT)")
        w.text(f"Vacuum: {self.fmt(self.frequency)}", fill=w.col_nav)
        if self.strike is not None:
            w.text(
                f"Also on STRIKE {self.fmt(self.strike)} when a radar touches your "
                "package's route or target.",
                fill=w.col_nav,
                wrap=True,
            )
        _lines(
            w,
            [
                "Vacuum is a listening plane. It hears enemy radars switch on and "
                "calls them. It never jams and never marks targets.",
                'It calls each radar as it comes on: "Vacuum, SA-6 awake, bullseye '
                '304/60, tight" = an SA-6 on now, 304 for 60 NM from bullseye.',
                "Awake: on now. Asleep: found, off now. Tight: within 1 NM. Loose: "
                "up to 15 NM off.",
            ],
        )
        w.rule()
        w.heading("Calls (say its name, then yours)")
        _lines(
            w,
            [
                f'"Vacuum, {me}, checking in."',
                f'  "{me}, Vacuum, two awake, one asleep, nearest SA-6 awake, '
                'bullseye 090/25, tight."',
                f'"Vacuum, {me}, say emitters."   3 nearest, awake first, FROM YOU:',
                f'  "{me}, Vacuum, SA-6 awake 270, 35, tight; SA-11 asleep 245, '
                '50, loose."',
                f'"Vacuum, {me}, request target status."   Radars it knows around '
                "your target:",
                f'  "{me}, Vacuum, target area, SA-6 awake, bullseye 095/22, loose."',
                f'"Vacuum, {me}, mud 270."   Which awake radar is your RWR spike?',
                f'  "{me}, Vacuum, mud 270 is SA-6 awake, bullseye 090/25, tight."',
                f'"Vacuum, {me}, say again."   It repeats its last call to you.',
                '"Blank": no radar found yet. "No emitter 270": nothing awake on '
                "that bearing.",
            ],
        )
        w.rule()
        w.heading("Radar names it uses")
        w.table(
            [list(row) for row in VACUUM_RADARS],
            headers=["It says", "What it is", "Reach"],
            font=w.content_font,
        )
        w.rule()
        w.heading("When it is silent")
        _lines(
            w,
            [
                "Before it is airborne, and after it lands or is shot down.",
                "A radar that blinks is called once; again after a full minute off, "
                "or once more when its fix goes tight.",
                *(
                    ["Casual radio discipline: it only calls radars near a package."]
                    if self.casual
                    else []
                ),
                'Nobody answers? Start with "Vacuum", check the frequency, say it '
                'again slower. Ask the AWACS for "picture", not Vacuum.',
            ],
        )
        w.text(
            "A SAM that never turns its radar on is invisible to Vacuum. "
            '"Blank" does not mean safe.',
            fill=w.col_caution,
            wrap=True,
        )
        w.write(path)
