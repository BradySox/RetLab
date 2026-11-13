# Local patches to the vendored `Moose.lua`

Read before bumping the bundle. Lifted 2026-10-12 from the framework-consolidation
note, whose MIST-retirement plan was reversed 2026-09-12 (`retlab-skynet-return-notes.md`).

The bundle is `resources/plugins/base/Moose.lua`, currently MOOSE develop commit `69bb1ad8`
(2026-11-08; `Moose_Include_Static/Moose_.lua` from MOOSE_INCLUDE, DM pick: develop). It carries fork edits that a naive re-vendor drops silently. Each is
marked in the file with a `-- RetLab patch (<subject>)` comment — grep for `RetLab patch`
before and after any bump and re-apply what is missing.

**Prefer a plugin-side monkeypatch to a bundle edit.** `intercept-config.lua` patches
`BASE.CreateEventTakeoff` from the plugin rather than editing the bundle, and that is the
right default: it survives a bump and carries its own removal trigger. Edit the bundle
only when the target is a `local` a plugin cannot reach.

| Patch | Why it is in the bundle | Removal trigger |
|---|---|---|
| `task-complete row` | `EVENTS.UnitTaskComplete` has no `_EVENTMETA` row upstream, so each task completion logs "Could not get EVENTMETA data" | Upstream adds the row |

**Bump of 2026-11-13** (`3a95e75c` to `69bb1ad8`): the `event 61 spam` and `LHA landing
error` patches dropped out (upstream develop carries both fixes). The two
`civilian_traffic crash guard` patches in RAT were not re-applied: no plugin uses MOOSE's
RAT since §129's redesign; if RAT comes back, recover them from this repo's history
(`git log -S "civilian_traffic crash guard" -- resources/plugins/base/Moose.lua`). MOOSE #2595 is not fixed upstream, so the intercept plugin's
`BASE.CreateEventTakeoff` monkeypatch stays. CTLD went 1.3.38 to 1.4.45; the internals
`ctld-config.lua` touches (`Loaded_Cargo`, `_UnloadTroops`, `PreloadTroops`) kept their shape.

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
