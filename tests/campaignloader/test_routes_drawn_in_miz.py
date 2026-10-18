"""Supply routes and shipping lanes are drawn in the campaign .miz, never the yaml.

DM call (2026-10-18): an M-113 group per road and a HandyWind group per sea lane,
as upstream campaigns draw them. ``tools/campaign_routes.py`` moved every yaml
``supply_routes:``/``shipping_lanes:`` list into its .miz.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CAMPAIGNS = sorted(Path("resources/campaigns").glob("*.yaml"))


@pytest.mark.parametrize("path", CAMPAIGNS, ids=lambda p: p.stem)
def test_routes_are_not_in_the_yaml(path: Path) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    assert "supply_routes" not in data, "draw roads as M-113 groups in the .miz"
    assert (
        "shipping_lanes" not in data
    ), "draw sea lanes as HandyWind groups in the .miz"
