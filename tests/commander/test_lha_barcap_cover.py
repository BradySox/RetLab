"""An LHA beside a friendly carrier gets no BARCAP of its own."""

from __future__ import annotations

from dataclasses import dataclass

from game.commander.theaterstate import lha_covered_by_carrier
from game.utils import nautical_miles


@dataclass
class _Ship:
    x_nm: float
    is_lha: bool = False
    is_carrier: bool = False

    def distance_to(self, other: _Ship) -> float:
        return nautical_miles(abs(self.x_nm - other.x_nm)).meters


def test_lha_next_to_a_carrier_is_covered() -> None:
    carrier = _Ship(0, is_carrier=True)
    lha = _Ship(60, is_lha=True)
    assert lha_covered_by_carrier(lha, [carrier, lha])  # type: ignore[arg-type,list-item]


def test_lone_lha_keeps_its_cap() -> None:
    carrier = _Ship(0, is_carrier=True)
    lha = _Ship(100, is_lha=True)
    assert not lha_covered_by_carrier(lha, [carrier, lha])  # type: ignore[arg-type,list-item]
    assert not lha_covered_by_carrier(lha, [lha])  # type: ignore[arg-type,list-item]


def test_carrier_is_never_dropped() -> None:
    carrier = _Ship(0, is_carrier=True)
    other = _Ship(1, is_carrier=True)
    assert not lha_covered_by_carrier(carrier, [carrier, other])  # type: ignore[arg-type,list-item]
