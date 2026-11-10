# RetLab PR #823 Frontline Merge Notes

The record of how upstream **PR #823, "Enhanced Front Line Stances + Movement"**
(`dcs-retribution/dcs-retribution#823`, branch `feat/dr-byba-frontline-movement`) sits in
the fork. Read this before syncing a newer #823, or before touching
`game/missiongenerator/flotgenerator.py` or `game/ground_forces/ai_ground_planner.py`.

| | |
|---|---|
| Adopted | 2026-06-26, by hand, in three buckets (A, B, C below) |
| Upstream state | Still an open PR on 2026-11-10 (head `9ad944a6d`, 4 commits) |
| Front-line driver | DCS's own ground AI. TIC was removed 2026-10-15 (features doc §9) |

## What #823 is

Two stacked features:

1. **Composition and spread.** Proportional mixed armor clusters (largest-remainder
   allocation, `anchor`-linked members, even-slot placement) replace single-type random
   groups.
2. **Cohesive maneuver.** Clusters move as a unit through DCS AI tasks and pydcs formations
   (Vee/Line), with per-stance advance distances and an APC-into-wedge fix.

Both run for every frontline role. The fork once guarded the maneuver half behind a
TIC-off check; that guard went with TIC.

## Bucket A — taken as-is

- `game/ground_forces/frontline_clustering.py`: `allocate_largest_remainder`,
  `even_slot_centers`. Identical to the PR head on 2026-11-10.
- `game/ground_forces/ai_ground_planner.py`: proportional allocation, `Cluster` /
  `assemble_clusters`, the `anchor` field with its `__setstate__` backfill (old saves load
  with `anchor = None`), the role tables.
- `default_front_line_stance` (`game/settings/fields/campaignmanagement.py`).
- `game/theater/controlpoint.py`: `seed_front_line_stances`,
  `apply_default_stance_on_capture` and the `capture()` call.
- `game/theater/start_generator.py`: `apply_default_player_stances` and the `generate()` call.
- Tests: `tests/ground_forces/`, `tests/theater/test_default_front_line_stance*`,
  `tests/test_default_front_line_stance_settings.py`.

## Bucket B — placement, merged with the fork's own

`flotgenerator.py` keeps both: #823's even spread **along** the front and the fork's
anti-stacking **off** the front.

- `get_valid_position_for_group(distance_from_frontline, spawn_heading, along_offset)`
  takes #823's `along_offset` for the lateral pick, clamped to the front's size.
- The depth search is the fork's: `_step_back` walks back from that point, with the
  degenerate-front guard (`is_on_land`) first.
- `_generate_groups` is #823's two-pass body: `frontline_offsets`, the wedge depth and
  jitter pre-pass, `CLUSTER_DEPTH_OFFSET`, `CLUSTER_LATERAL_JITTER`.
- `_generate_group` passes #823's `move_formation` to `vehicle_group(...)`.
- Infantry uses #823's forward lead and scatter (`INFANTRY_FORWARD_OFFSET`,
  `INFANTRY_SCATTER_RADIUS`).

## Bucket C — maneuver dispatch

`plan_action_for_groups` routes each role:

| Role | Action |
|---|---|
| ARTILLERY | `_plan_artillery_action`, when `perf_artillery` is on and a target is in range |
| TANK, IFV, APC | `_plan_tank_ifv_action` (the APC joins the wedge) |
| ATGM, SHORAD, RECON with an `anchor` | `_plan_follower_action` |
| ATGM, SHORAD, RECON without one | `_plan_apc_atgm_action` |

The shared RETREAT block runs after the branch. `_plan_follower_action` returns `False` on
RETREAT so the retreat waypoints are added once.

`tests/missiongenerator/test_flotgenerator_maneuver_dispatch.py` locks this table.

## Where the fork differs from #823 — keep these on a sync

- **Deployment denominator.** `plan_groundwar` divides by `base.total_frontline_units`
  (the frontline-eligible classes), not #823's `total_armor`. The test fakes set
  `total_frontline_units`.
- **`CombatStance` is in `SERIALIZABLE_ENUM_TYPES`** (`game/settings/enums.py`). The fork
  loads settings enums from a registry; upstream's loader did not need the entry.
- **Anti-stacking depth search** (`_step_back`), as in Bucket B.
- **The bowed front.** When `conflict.bounds` is set, the lateral point comes from
  `bounds.point_at(clamped)` (features doc §90), and each group gets its own forward
  heading from `_forward`.
- **Hold fixes.** `tests/missiongenerator/test_flotgenerator_hold.py` covers a negative
  hold time and defenders waiting on enemy CAS. Neither is in #823.

Measured against the PR head on 2026-11-10: `flotgenerator.py` differs by 361 added and
137 removed lines, `ai_ground_planner.py` by 96 and 71. Both sides have moved since the
adoption (the fork's §90 and §56 work, the PR's rebase onto a newer `dev`), so a sync is a
3-way merge, not a copy.

## When #823 changes or merges upstream

1. Diff the PR against the files above; `frontline_clustering.py` should still match.
2. Re-apply the five differences in the list above.
3. Run `tests/ground_forces`, the four `tests/missiongenerator/test_flotgenerator_*`
   files and the default-stance tests.
4. The laydown is a spawn-time behavior no test flies. Check the front in a generated
   mission.
5. Record the sync in `docs/dev/retlab-upstreaming-inventory.md`, which carries the
   divergence entry for this PR.

## History

Drafted 2026-06-26 against a build where TIC drove the front line; the three buckets
landed the same day. The TIC-era text, including the `not self.tic_enabled` guard and its
test, is at `git show a32da7721:docs/dev/design/retlab-pr823-frontline-merge-notes.md`.
