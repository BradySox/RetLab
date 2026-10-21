"""The first Voice AWACS default, Sentinel, is now an ABCCC name (2026-10-21)."""

from game.settings.migration import migrate_legacy_settings


def test_a_lone_sentinel_becomes_the_rotation() -> None:
    migrated = migrate_legacy_settings({"voice_awacs_callsign": "Sentinel"})
    assert migrated["voice_awacs_callsign"] == "Chalice, Chainsaw, Image"


def test_a_chosen_list_is_kept() -> None:
    migrated = migrate_legacy_settings({"voice_awacs_callsign": "Magic, Sentinel"})
    assert migrated["voice_awacs_callsign"] == "Magic, Sentinel"
