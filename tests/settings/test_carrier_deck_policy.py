from game.settings import Settings
from game.settings.migration import migrate_legacy_settings
from game.settings.enums import CarrierDeckPolicy


def test_both_old_keys_are_dropped_from_a_save() -> None:
    migrated = migrate_legacy_settings(
        {
            "player_flights_sixpack": True,
            "carrier_deck_policy": CarrierDeckPolicy.LAST_RESORT,
        }
    )
    assert "player_flights_sixpack" not in migrated
    assert "carrier_deck_policy" not in migrated


def test_the_setting_is_gone() -> None:
    names = {
        name
        for page in Settings.pages()
        for section in Settings.sections(page)
        for name, _description in Settings.fields(page, section)
    }
    assert "carrier_deck_policy" not in names
    assert not hasattr(Settings(), "carrier_deck_policy")
