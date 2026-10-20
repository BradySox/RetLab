"""Cheat sheets for the voice controllers (§116, §117): the ABCCC and SkyEye's AWACS.

Written for pilots new to talking to a bot on SRS: who is who, which frequency, the
exact words to say, what the answers mean, and what to do when nobody answers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from game.radio.radios import RadioFrequency
from ..kneeboard_page import KneeboardPage
from .writer import KneeboardPageWriter


def _freq(frequency: RadioFrequency) -> str:
    return f"{frequency.mhz:.3f} {frequency.modulation.name}"


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
    ) -> None:
        self.controller = controller
        self.strike = strike
        self.awacs = awacs
        self.callsign = callsign
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        w = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        c, me = self.controller, self.callsign
        w.title(f"Talking to {c} (ABCCC)")
        w.text(f"STRIKE: {_freq(self.strike)}", fill=w.col_nav)
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
                f'"{c}, {me}, check in."',
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
                '"Radar contact ... angels 20, push time 14 32": go to your HOLD '
                "point at that altitude and wait.",
                '"Push, push": leave the HOLD now for the target.',
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
    ) -> None:
        self.awacs = awacs
        self.frequency = frequency
        self.strike = strike
        self.callsign = callsign
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        w = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        a, me = self.awacs, self.callsign
        w.title(f"Talking to {a} (AWACS)")
        w.text(f"{a}: {_freq(self.frequency)}", fill=w.col_nav)
        if self.strike is not None:
            w.text(
                f"Also on STRIKE {_freq(self.strike)} for threats and your calls.",
                fill=w.col_nav,
                wrap=True,
            )
        _lines(
            w,
            [
                f"{a} is a voice AWACS (SkyEye). It sees the air picture and answers "
                "when you talk to it.",
                "It knows you by your DCS player name, e.g. 'Viper 1 | Joe' is "
                "VIPER 1. Call yourself that.",
            ],
        )
        w.rule()
        w.heading("Calls")
        _lines(
            w,
            [
                f'"{a}, {me}, radio check."   Can it hear you?',
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
