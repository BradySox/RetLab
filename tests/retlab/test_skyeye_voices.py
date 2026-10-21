"""SkyEye voices by squadron country (§117)."""

from __future__ import annotations

import random

from game.retlab.skyeye_voices import (
    ACCENT_VOICES,
    accent_for,
    pick_another_voice,
    pick_voices,
)


def test_accents_by_country() -> None:
    assert accent_for("USA") == "american"
    assert accent_for("UK") == "british"
    assert accent_for("Saudi Arabia") == "arabic"
    assert accent_for("South Korea") == "british"
    assert accent_for("China") == "british"
    assert accent_for(None) == "british"


def test_the_two_voices_are_never_the_same_gender() -> None:
    rng = random.Random(4)
    genders = {name: g for pool in ACCENT_VOICES.values() for name, g in pool}
    for _ in range(50):
        awacs, abccc = pick_voices("USA", "Saudi Arabia", rng)
        assert genders[awacs] != genders[abccc]
        assert awacs in dict(ACCENT_VOICES["american"])
        assert abccc in dict(ACCENT_VOICES["arabic"])


def test_every_accent_has_both_genders() -> None:
    for accent, pool in ACCENT_VOICES.items():
        assert {g for _, g in pool} == {"m", "f"}, accent


def test_vacuum_takes_a_voice_neither_other_bot_has() -> None:
    taken = ["kokoro#am_eric", "kokoro#af_heart"]
    for seed in range(20):
        voice = pick_another_voice("USA", taken, random.Random(seed))
        assert voice not in taken
        assert voice.startswith("kokoro#a")


def test_a_full_accent_borrows_another() -> None:
    taken = [v for v, _ in ACCENT_VOICES["american"]]
    assert pick_another_voice("USA", taken, random.Random(1)) not in taken
