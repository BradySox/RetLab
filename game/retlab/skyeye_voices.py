"""SkyEye voices by squadron country (§117): the AWACS and the ABCCC sound like their crews.

Each name is a Piper voice folder under SkyEye's voices directory, with ``#speaker`` for one
speaker of a multi-speaker model. L2-ARCTIC is English read by native speakers of other
languages, the nearest Piper has to a foreign accent; RetLab uses its Arabic and Spanish
speakers only (user call, 2026-10-20). SkyEye falls back to its own voice
when a voice is missing. docs/dev/retlab-features.md §117.
"""

from __future__ import annotations

import random
from typing import Optional

L2 = "en_US-l2arctic-medium#"

#: (voice, "m" or "f") by accent.
ACCENT_VOICES: dict[str, tuple[tuple[str, str], ...]] = {
    "american": (
        ("en_US-ryan-medium", "m"),
        ("en_US-joe-medium", "m"),
        ("en_US-amy-medium", "f"),
        ("en_US-kristin-medium", "f"),
    ),
    "british": (
        ("en_GB-alan-medium", "m"),
        ("en_GB-northern_english_male-medium", "m"),
        ("en_GB-cori-medium", "f"),
        ("en_GB-alba-medium", "f"),
    ),
    "arabic": (
        (L2 + "ABA", "m"),
        (L2 + "YBAA", "m"),
        (L2 + "SKA", "f"),
        (L2 + "ZHAA", "f"),
    ),
    "spanish": (
        (L2 + "EBVS", "m"),
        (L2 + "ERMS", "m"),
        (L2 + "MBMPS", "f"),
        (L2 + "NJS", "f"),
    ),
}

#: DCS country name -> accent. Anyone not listed sounds British.
COUNTRY_ACCENTS: dict[str, str] = {
    **dict.fromkeys(
        ["USA", "Canada", "Combined Joint Task Forces Blue", "USAF Aggressors"],
        "american",
    ),
    **dict.fromkeys(
        [
            "Saudi Arabia",
            "United Arab Emirates",
            "Qatar",
            "Kuwait",
            "Bahrain",
            "Oman",
            "Jordan",
            "Egypt",
            "Iraq",
            "Syria",
            "Lebanon",
            "Libya",
            "Algeria",
            "Morocco",
            "Tunisia",
            "Yemen",
            "Sudan",
        ],
        "arabic",
    ),
    **dict.fromkeys(
        [
            "Spain",
            "Mexico",
            "Argentina",
            "Chile",
            "Venezuela",
            "Peru",
            "Cuba",
            "Ecuador",
            "Bolivia",
            "Brazil",
        ],
        "spanish",
    ),
}


def accent_for(country_name: Optional[str]) -> str:
    return COUNTRY_ACCENTS.get(country_name or "", "british")


def pick_voices(
    awacs_country: Optional[str],
    abccc_country: Optional[str],
    rng: Optional[random.Random] = None,
) -> tuple[str, str]:
    """The AWACS and ABCCC voices: each from its own crew's accent, never the same gender."""
    rng = rng or random.Random()
    awacs_pool = ACCENT_VOICES[accent_for(awacs_country)]
    awacs, awacs_gender = rng.choice(awacs_pool)
    abccc_pool = [
        v
        for v in ACCENT_VOICES[accent_for(abccc_country)]
        if v[1] != awacs_gender and v[0] != awacs
    ]
    abccc = rng.choice(abccc_pool)[0] if abccc_pool else awacs_pool[0][0]
    return awacs, abccc


def pick_another_voice(
    country: Optional[str], taken: list[str], rng: Optional[random.Random] = None
) -> str:
    """A voice from the crew's accent that no other bot this mission speaks with (§118)."""
    rng = rng or random.Random()
    pool = [v for v, _ in ACCENT_VOICES[accent_for(country)] if v not in taken]
    if not pool:
        pool = [
            v for voices in ACCENT_VOICES.values() for v, _ in voices if v not in taken
        ]
    return rng.choice(pool)
