"""A fit in the user's UnitPayloads folder must not replace a shipped preset.

pydcs's ``PayloadDirectories.payload_dirs`` yields the user's
``MissionEditor/UnitPayloads`` ahead of the shipped payloads even when it is not
registered. On 2026-10-21 a "Retribution DEAD" saved there on 2026-08-22 put
AGM-78B, a mod store, on a planned F-4E DEAD flight (features doc §73).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from dcs.payloads import PayloadDirectories
from dcs.planes import FA_18C_hornet

from game.dcs.payloadpatch import patch_pydcs_payload_loader

FIT = """local unitPayloads = {{
\t["name"] = "FA-18C_hornet",
\t["payloads"] = {{
\t\t[1] = {{
\t\t\t["name"] = "Retribution DEAD",
\t\t\t["pylons"] = {{
\t\t\t\t[1] = {{ ["CLSID"] = "{clsid}", ["num"] = 2 }},
\t\t\t}},
\t\t\t["tasks"] = {{ [1] = 11 }},
\t\t}},
\t}},
\t["unitType"] = "FA-18C_hornet",
}}
return unitPayloads
"""


@pytest.fixture
def user_and_shipped(tmp_path: Path) -> Iterator[Path]:
    from dcs.unittype import FlyingType

    user = tmp_path / "UnitPayloads"
    shipped = tmp_path / "customized_payloads"
    user.mkdir()
    shipped.mkdir()
    (user / "FA-18C_hornet.lua").write_text(
        FIT.format(clsid="{USER_STORE}"), encoding="utf-8"
    )
    (shipped / "FA-18C_hornet.lua").write_text(
        FIT.format(clsid="{SHIPPED_STORE}"), encoding="utf-8"
    )

    saved = (
        PayloadDirectories._user,
        PayloadDirectories._dcs,
        PayloadDirectories._mod,
        PayloadDirectories.preferred,
        PayloadDirectories.fallback,
    )
    saved_cache = dict(FlyingType._payload_cache or {})
    saved_payloads = FA_18C_hornet.payloads
    PayloadDirectories._user = user
    PayloadDirectories._dcs = []
    PayloadDirectories._mod = []
    PayloadDirectories.preferred = None
    PayloadDirectories.fallback = shipped
    FlyingType._payload_cache = {}
    FA_18C_hornet.payloads = None
    try:
        yield user
    finally:
        (
            PayloadDirectories._user,
            PayloadDirectories._dcs,
            PayloadDirectories._mod,
            PayloadDirectories.preferred,
            PayloadDirectories.fallback,
        ) = saved
        FlyingType._payload_cache = saved_cache
        FA_18C_hornet.payloads = saved_payloads


def test_the_shipped_preset_wins_its_name(user_and_shipped: Path) -> None:
    patch_pydcs_payload_loader()
    fit = FA_18C_hornet.load_payloads()["Retribution DEAD"]
    assert [p["CLSID"] for p in fit["pylons"].values()] == ["{SHIPPED_STORE}"]


def test_a_user_only_fit_is_not_offered(user_and_shipped: Path) -> None:
    (user_and_shipped / "FA-18C_hornet.lua").write_text(
        FIT.format(clsid="{USER_STORE}").replace("Retribution DEAD", "My DEAD"),
        encoding="utf-8",
    )
    patch_pydcs_payload_loader()
    assert "My DEAD" not in FA_18C_hornet.load_payloads()
