"""Missile families whose newer variant replaces an older one on the same pylon.

The date restriction only steps a weapon down its fallback chain, so a fit carrying
an AIM-9L stays an AIM-9L in a 2020 campaign. The shipped presets carry the newest
variant (#1273) and saved loadouts are stepped up on load (§128). Clear upgrades
only (2026-10-17 DM call): not AIM-9L to AIM-9P, no seeker swaps, no mod-only
missiles.
"""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from game.data.weapons import Pylon, Weapon

FAMILIES = (
    ("AIM-9B", "AIM-9J", "AIM-9L", "AIM-9M", "AIM-9X"),
    ("2xAIM-9B", "2xAIM-9J", "2xAIM-9L", "2xAIM-9M", "2xAIM-9X"),
    ("AIM-7E", "AIM-7E-2", "AIM-7F", "AIM-7M"),
    ("AGM-65G", "AGM-65K"),
    ("R-27R", "R-27ER"),
    ("AGM-45A Shrike ARM", "AGM-45B Shrike ARM (Imp)"),
)
RANK = {
    group: (f, r) for f, family in enumerate(FAMILIES) for r, group in enumerate(family)
}
# A newer store on a different rack or adapter is not the same fit.
SAME_FIT_SIMILARITY = 0.6


def newer_variant(pylon: Pylon, weapon: Weapon) -> Optional[Weapon]:
    """The newest variant of ``weapon``'s family the pylon takes on the same rack."""
    rank = RANK.get(weapon.weapon_group.name)
    if rank is None:
        return None
    best: Optional[Weapon] = None
    best_rank = rank[1]
    # Sorted so a tie between two racks resolves the same way every run.
    for candidate in sorted(pylon.allowed, key=lambda w: w.clsid):
        candidate_rank = RANK.get(candidate.weapon_group.name)
        if (
            candidate_rank is not None
            and candidate_rank[0] == rank[0]
            and candidate_rank[1] > best_rank
            and difflib.SequenceMatcher(None, candidate.name, weapon.name).ratio()
            >= SAME_FIT_SIMILARITY
        ):
            best, best_rank = candidate, candidate_rank[1]
    return best
