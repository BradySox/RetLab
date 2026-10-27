"""The Radio discipline setting (§121) is gone; old saves drop it cleanly."""

from game.settings import Settings
from game.settings.enums import RadioDiscipline
from game.settings.migration import migrate_legacy_settings


def test_both_old_keys_are_dropped_from_a_save() -> None:
    migrated = migrate_legacy_settings(
        {"voice_atc_strict": False, "radio_discipline": RadioDiscipline.CASUAL}
    )
    assert "voice_atc_strict" not in migrated
    assert "radio_discipline" not in migrated


def test_the_setting_is_gone() -> None:
    names = {
        name
        for page in Settings.pages()
        for section in Settings.sections(page)
        for name, _description in Settings.fields(page, section)
    }
    assert "radio_discipline" not in names
    assert not hasattr(Settings(), "radio_discipline")


def test_a_save_holding_the_setting_still_loads() -> None:
    settings = Settings()
    state = dict(settings.__dict__)
    state["radio_discipline"] = RadioDiscipline.STRICT
    settings.__setstate__(state)
    assert not hasattr(settings, "radio_discipline")
