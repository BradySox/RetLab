"""A campaign that placed the IADS buildings runs in range mode, flag or no flag.

`advanced_iads: true` only chooses the network mode; what range mode consumes is
the command centre, comms tower and power station statics the author placed in
the miz. Three shipped campaigns placed them without the flag, so their SAMs
were never wired to the buildings standing beside them. The buildings now
decide, and the New Game wizard's Advanced IADS box is the per-game opt-out.
Nothing is placed: a campaign with no buildings stays basic.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from game.campaignloader.campaign import Campaign
from game.campaignloader.mizcampaignloader import miz_carries_iads_infrastructure

CAMPAIGNS = Path("resources/campaigns")


def _miz(tmp_path: Path, mission: bytes) -> Path:
    path = tmp_path / "campaign.miz"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mission", mission)
    return path


def _campaign(tmp_path: Path, mission: bytes, extra_yaml: str = "") -> Campaign:
    _miz(tmp_path, mission)
    yaml_path = tmp_path / "campaign.yaml"
    yaml_path.write_text(
        "name: T\ntheater: caucasus\nmiz: campaign.miz\n" + extra_yaml,
        encoding="utf-8",
    )
    return Campaign.from_file(yaml_path)


def test_each_of_the_three_statics_counts_as_infrastructure(tmp_path: Path) -> None:
    # The DCS ids, as the mission file writes them: the comms tower is spelled
    # with spaces, not the pydcs class name's underscores.
    for unit_id in ("GeneratorF", "Comms tower M", ".Command Center"):
        mission = f'["type"] = "{unit_id}",'.encode()
        assert miz_carries_iads_infrastructure(_miz(tmp_path, mission)), unit_id


def test_a_miz_without_them_and_a_missing_miz_do_not(tmp_path: Path) -> None:
    assert not miz_carries_iads_infrastructure(_miz(tmp_path, b'["type"] = "Hawk sr",'))
    assert not miz_carries_iads_infrastructure(tmp_path / "absent.miz")


def test_a_campaign_that_placed_a_power_station_promotes(tmp_path: Path) -> None:
    campaign = _campaign(tmp_path, b'["type"] = "GeneratorF",')
    assert campaign.advanced_iads is True


def test_a_campaign_with_no_buildings_stays_basic(tmp_path: Path) -> None:
    campaign = _campaign(tmp_path, b'["type"] = "Hawk sr",')
    assert campaign.advanced_iads is False
    campaign = _campaign(
        tmp_path, b'["type"] = "Hawk sr",', extra_yaml="advanced_iads: false\n"
    )
    assert campaign.advanced_iads is False


def test_the_buildings_win_over_an_explicit_false(tmp_path: Path) -> None:
    # Desert Sabre writes `advanced_iads: false` over 12 power stations. Only
    # four yamls write false at all, so the word carries no intent; the
    # wizard's box is the opt-out.
    campaign = _campaign(
        tmp_path, b'["type"] = "GeneratorF",', extra_yaml="advanced_iads: false\n"
    )
    assert campaign.advanced_iads is True


@pytest.mark.parametrize(
    "name", ["Operation-Desert-Sabre", "operation_allied_sword", "RetakeTheFalklands"]
)
def test_the_shipped_campaigns_that_placed_buildings_promote(name: str) -> None:
    # Measured 2026-09-21: Desert Sabre 12 comms towers and 12 power stations,
    # Allied Sword a command centre and 2 power stations, the Falklands 2 command
    # centres and a comms tower. None of the three yamls set the flag to true.
    campaign = Campaign.from_file(CAMPAIGNS / f"{name}.yaml")
    assert not campaign.data.get("advanced_iads", False)
    assert campaign.advanced_iads is True


def test_a_flagged_campaign_is_unchanged() -> None:
    assert Campaign.from_file(CAMPAIGNS / "red_tide.yaml").advanced_iads is True
