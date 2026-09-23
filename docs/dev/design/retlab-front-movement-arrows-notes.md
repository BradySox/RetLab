# Front movement arrows — design note (2026-09-23)

Status: **BUILT 2026-09-23, not flown** (features doc §90, checklist B139). Concept from
FinCenturion's movement indicators (his Discord post 2026-09-15; §12 of
[retlab-fincenturion-dist-notes.md](retlab-fincenturion-dist-notes.md)). His code is not
read or copied.

## 1. The idea

Show on the map which way each front moved last turn and how far, and blue's own stance.
Display only: nothing about how the front moves changes.

## 2. Why the §90 gate does not block it

The gate on §90 work is "extending an untested model buries the test" (B65 PARTIAL, B66
UNTESTED). An arrow changes no rule. It makes B66 — "over 3–4 turns a pushed front moves at a
cost, a defensive front holds, the line does not see-saw" — **readable from the map** instead
of from saves. It helps close the gate rather than burying it.

Retreat along the attack's axis is different: it changes behaviour, and stays gated (§5.2 of
the FinCenturion note).

## 3. What exists

- **Nothing shows direction.** `FrontLineJs` (`game/server/frontlines/models.py:18`) carries
  `id` and `extents` only. `FrontLine.tsx` draws a line; the tooltip reads "Front line". The
  F10 drawing (`drawingsgenerator.py:122`) is a polyline.
- **No history.** `FrontLine.position` is the current value only (`frontline.py:106`),
  recomputed each turn. `update_position()` runs at `game.py:562` and
  `missionresultsprocessor.py:637`. The only trace is the text "Frontline Report" message, with
  no distance.
- **The direction is available.** `blue_forward_heading` (`frontline.py:45`) and
  `advance_heading` (`frontlineconflictdescription.py:55`).
- **Stance never reaches the web map.** `ControlPoint.stances[enemy_cp.id]`
  (`combat_stance.py`) is read only by Qt and the briefing.

## 4. What it needs

1. Persist the previous position on `FrontLine`: `settle_position()` in `finish_turn` stores
   `previous_progress` / `settled_progress`, read through `getattr` so a pre-feature save has
   no arrow rather than a migration. `hold_position()` clears it on a skipped turn.
2. `FrontMovementJs` on `FrontLineJs.movement`, with the arrow's shaft and head computed
   server-side from `blue_forward_heading`, and the client type (`_liberationApi.ts`).
3. An arrow at the line's midpoint, pointing the way it moved, scaled by distance; none under a
   threshold. Tooltip: "Advanced 4.2 NM toward X — blue aggressive, red defensive".
4. A layer row in `MapLayersControl.tsx` in the "Friendly & shared" group with
   `enabledWhen: frontLines`.

## 5. Rules

- **Fog.** The front line is shared knowledge; its movement is too. Red's stance is not — show
  blue's own stance only, or read the stance off the outcome, until the DM says otherwise.
- UI text: NM, US English, per the house style.

## 6. Tests

A server model test for the delta and its sign; a client layer-count test (the existing layer
tests count rows — update them); the migration.

## 7. In-game pass (a checklist row when built)

App check over 3 turns: the arrow points the way the line moved in the saves, its length
matches, and a held front shows none. That is also B66's evidence.
