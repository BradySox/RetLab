"""An AI landing on a ship with no arresting wires must not read a wire.

Test 55 (2026-10-11): an AV-8B landed on LHA-1 Tarawa and `dcs.log` carried
`Moose.lua:65562: attempt to compare number with nil` from `AIRBOSS:_GetWire`.
`AIRBOSS:OnEventLand` guards its AI wire lookup with a chain of `~=` tests on the
carrier type. The bundled build joined them with `or`, which is true for every
ship, so the Tarawa (wire1..4 are nil) reached `_GetWire` and the error skipped
`_RecoveredElement`. Upstream develop joins them with `and`.

The guard is lifted out of the shipped Moose.lua and run on Lua 5.1, so a bundle
bump that brings the `or` back fails here.
"""

from __future__ import annotations

import re
from pathlib import Path

import lupa.lua51
import pytest

MOOSE = Path("resources/plugins/base/Moose.lua")

#: Ships with no wires: AIRBOSS:_Init<ship> sets carrierparam.wire1..4 to nil.
NO_WIRES = ["INVINCIBLE", "HERMES", "TARAWA", "AMERICA", "JCARLOS", "CANBERRA"]
WIRED = ["LINCOLN", "STENNIS", "FORRESTAL", "KUZNETSOV"]


def _moose() -> str:
    return MOOSE.read_text(encoding="utf-8", errors="ignore")


def _ai_landing_guard() -> str:
    """The condition in front of the AI branch's `_GetWire(coord,0)` call."""
    match = re.search(
        r"\nif (self\.carriertype~=AIRBOSS\.CarrierType\.[^\n]*?) then\r?\n"
        r"local coord=EventData\.IniUnit:GetCoordinate\(\)\r?\n"
        r"local dist=coord:Get2DDistance\(self:GetCoordinate\(\)\)\r?\n"
        r"local wire=self:_GetWire\(coord,0\)",
        _moose(),
    )
    assert match, (
        "could not find the AI wire lookup in AIRBOSS:OnEventLand. The bundle "
        "changed; re-point this test rather than deleting it."
    )
    return match.group(1)


def _carrier_types() -> dict[str, str]:
    match = re.search(r"\nAIRBOSS\.CarrierType=\{(.*?)\n\}", _moose(), re.DOTALL)
    assert match, "could not find AIRBOSS.CarrierType in Moose.lua"
    return dict(re.findall(r'(\w+)="([^"]*)"', match.group(1)))


def _reads_a_wire(ship: str) -> bool:
    types = _carrier_types()
    assert ship in types, f"{ship} is not an AIRBOSS carrier type any more"
    lua = lupa.lua51.LuaRuntime(unpack_returned_tuples=False)
    carrier_types = lua.table()
    for key, value in types.items():
        carrier_types[key] = value
    guard = lua.eval(
        "function(carriertype, types)\n"
        "  local self = { carriertype = carriertype }\n"
        "  local AIRBOSS = { CarrierType = types }\n"
        f"  return ({_ai_landing_guard()})\n"
        "end"
    )
    return bool(guard(types[ship], carrier_types))


@pytest.mark.parametrize("ship", NO_WIRES)
def test_an_ai_landing_on_a_ship_with_no_wires_skips_the_wire_lookup(
    ship: str,
) -> None:
    assert not _reads_a_wire(ship)


@pytest.mark.parametrize("ship", WIRED)
def test_an_ai_landing_on_a_wired_carrier_still_reads_its_wire(ship: str) -> None:
    assert _reads_a_wire(ship)
