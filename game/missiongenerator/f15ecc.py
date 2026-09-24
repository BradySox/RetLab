"""F-15E smart-weapon CC mission numbering, shared by the .miz writer and the kneeboard.

Limits are from the F-15E Manual v1.7, 13.4.7.4-5: 8 missions a set and 40 across all
sets. The jet shows a loaded mission as "CC set/mission" on the Smart Weapons page.
"""

from __future__ import annotations

from typing import Optional

MISSIONS_PER_SET = 8
MAX_MISSIONS = 40


def cc_mission(index: int) -> Optional[tuple[int, int]]:
    """(set, mission) for the index-th CC mission, or None past the jet's 40."""
    if index < 0 or index >= MAX_MISSIONS:
        return None
    return index // MISSIONS_PER_SET + 1, index % MISSIONS_PER_SET + 1


def next_free_set_index(used: int) -> int:
    """First mission index of a fresh set after ``used`` missions, never set 1."""
    sets_used = max(1, -(-used // MISSIONS_PER_SET))
    return sets_used * MISSIONS_PER_SET
