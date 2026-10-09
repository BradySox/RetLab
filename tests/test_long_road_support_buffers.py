"""Long Road to H3 pins tight AEW&C/tanker buffers.

A red SA-5's 138 NM ring reaches 34 NM past Incirlik, so the stock 80/70 NM buffers
stood the Incirlik E-3 and KC-135s 105-150 NM north, off the Syria map (DM call
2026-10-08). At 20 NM they sit 56-100 NM north, still outside the ring.
"""

from __future__ import annotations

from pathlib import Path

from game.campaignloader.campaign import Campaign
from game.settings import Settings

_CAMPAIGN = (
    Path(__file__).resolve().parents[1]
    / "resources"
    / "campaigns"
    / "syria_TheLongRoadToH3.yaml"
)


def test_long_road_to_h3_tightens_support_orbits() -> None:
    campaign = Campaign.from_file(_CAMPAIGN)
    settings = Settings()
    settings.__dict__.update(Settings.deserialize_state_dict(campaign.settings))
    assert settings.aewc_threat_buffer_min_distance == 20
    assert settings.tanker_threat_buffer_min_distance == 20
