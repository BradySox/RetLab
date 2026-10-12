# Local patches to the vendored `Moose.lua`

Read before bumping the bundle. Lifted 2026-10-12 from the framework-consolidation
note, whose MIST-retirement plan was reversed 2026-09-12 (`retlab-skynet-return-notes.md`).

The bundle is `resources/plugins/base/Moose.lua`, currently MOOSE commit `3a95e75c`
(2025-10-13). It carries fork edits that a naive re-vendor drops silently. Each is
marked in the file with a `-- RetLab patch (<subject>)` comment — grep for `RetLab patch`
before and after any bump and re-apply what is missing.

**Prefer a plugin-side monkeypatch to a bundle edit.** `intercept-config.lua` patches
`BASE.CreateEventTakeoff` from the plugin rather than editing the bundle, and that is the
right default: it survives a bump and carries its own removal trigger. Edit the bundle
only when the target is a `local` a plugin cannot reach.

| Patch | Why it is in the bundle | Removal trigger |
|---|---|---|
| `civilian_traffic crash guard` (2 sites) | Orphan RAT spawns crashed the sim | Upstream fixes the orphan case |
| `event 61 spam` | `EVENT:onEvent` is bundle code; upstream develop already carries the same guard | The bundle is bumped past upstream's `if Event.id ~= 61` guard |
| `LHA landing error` | `AIRBOSS:OnEventLand` is bundle code; upstream develop already joins the tests with `and` | The bundle is bumped past that fix; `tests/lua/test_airboss_lha_landing.py` fails if a bump brings the `or` back |

## `LHA landing error` (2026-10-11, test 55)

`AIRBOSS:OnEventLand` reads the trapped wire for an AI landing unless the ship is one of
the six with no wires (Invincible, Hermes, Tarawa, America, Juan Carlos, Canberra). The
bundled build joined the six `~=` tests with `or`, which is true for every ship, so an AI
landing on LHA-1 reached `_GetWire`, compared a distance against `carrierparam.wire1`
(nil on those ships) and raised `attempt to compare number with nil`. The error also
skipped `_RecoveredElement` and `_CheckSectionRecovered` for that aircraft. One hit in
test 55, when the strike Harrier landed on the Tarawa; it repeats on every AI landing on
such a ship with the `airboss` plugin on.

**The fix** is upstream develop's: the six tests joined with `and`, marked
`-- RetLab patch (LHA landing error)`.

## `event 61 spam` (2026-08-29, re-fixed 2026-09-13)

**The 2026-08-29 fix was inert.** It assumed event 61 was `S_EVENT_UNIT_TASK_COMPLETE`
and added `_EVENTMETA` rows for `UnitTaskComplete` and `UnitTaskStage`. Those are ids 49
and 50 (Hoggit's `world.event` table; `S_EVENT_MAX` was 61 before 2.9.29). The first
flight on a build carrying the rows (2026-09-13, Iraq, DCS 2.9.29.27468) logged the line
~10,300 times in 20 minutes, with the patched bundle confirmed inside the flown `.miz`.

**What 61 is.** A new DCS 2.9.29 event that upstream MOOSE develop guards with
`if Event.id ~= 61 then` and the comment "seems to have no real data to be useable,
something like option changed". Its rate matches TIC's `Controller:setOption` churn
(~10-15/s on an active front), which is also what `debrief.log` records as
`group change option`. It is raised by our own ROE cycling and carries nothing.

**The fix now** is that same guard in `EVENT:onEvent`'s else-branch, marked
`-- RetLab patch (event 61 spam)`. The 49/50 rows stay: they are upstream-shaped and
harmless, and their comment now says what they are. Log volume only; no behaviour changes.

Measured before the fix: 6,807 occurrences on a 7-minute Afghanistan turn, 11,861 in an
archived Germany Cold War log, 63,338 suppressed copies on a 72-minute Iron Gate turn.
