"""Voice ATC's old "Strict readbacks" folds into the shared Radio discipline."""

from game.settings.enums import RadioDiscipline
from game.settings.migration import migrate_legacy_settings


def test_strict_readbacks_unticked_becomes_relaxed() -> None:
    migrated = migrate_legacy_settings({"voice_atc_strict": False})
    assert migrated["radio_discipline"] is RadioDiscipline.RELAXED
    assert "voice_atc_strict" not in migrated


def test_strict_readbacks_ticked_keeps_the_default() -> None:
    migrated = migrate_legacy_settings({"voice_atc_strict": True})
    assert "radio_discipline" not in migrated
    assert "voice_atc_strict" not in migrated


def test_a_saved_radio_discipline_wins() -> None:
    migrated = migrate_legacy_settings(
        {"voice_atc_strict": False, "radio_discipline": RadioDiscipline.CASUAL}
    )
    assert migrated["radio_discipline"] is RadioDiscipline.CASUAL
