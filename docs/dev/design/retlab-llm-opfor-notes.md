# Outside AI for red: read and report first, commander later · §109

**Status:** stage 1 (read and report) built 2026-10-09, not flown (row B201). Stage 2a
(the AI plans red) built 2026-10-09, not flown (row B204). Stages 2b and 3 agreed, not
started.

## The call, and what it reverses

On 2026-08-24 the DM said *"Long term I don't want the LLM planning red, I wanna use the
LLM to teach the model/Retribution to plan better"*, and the doctrine-mining note recorded
that no LLM runs in this fork. **On 2026-10-09 the DM reversed that**, after reading
juanjux's Escalation README, where the LLM commander is the headline feature:

> Defer to his version, read and report is the primary task for ours.

So RetLab builds Juan's shape (an outside AI that can eventually plan red), and its main
job is the one the August call wanted: an AI that reads red's turn and reports defects,
which we then fix in ordinary planner code. Seam 7 is still dropped as a claim about red's
quality ([retlab-red-brain-phase0-notes.md](retlab-red-brain-phase0-notes.md)); this is a
tool, not evidence that the HTN plans badly.

## Stages

| Stage | What | Status |
|---|---|---|
| 1 | Read API under `/retribution-ai/*` (REST), the `/start` and `/howtoplay` briefings, Developer tools > Copy AI connect link | Built 2026-10-09 |
| 2a | Packages (create, evaluate, delete, TOT), front stances, buying and selling aircraft and ground units, the AI's notes saved with the campaign, the Outside AI plans red switch, the Take Off fallback | Built 2026-10-09 |
| 2b | Loadouts, waypoint edits, ground transfers, ship moves, repairs, squadron moves | Agreed, not started |
| 3 | MCP at `/mcp` for the claude.ai app; the toolbar activity icon and the Take Off lock while the AI works | Agreed, not started |

DM's answers on 2026-10-09: port Juan's code; red sees blue as the scripted planner does,
never blue's ATO; the old planner fills in if the AI does not finish. For stage 2: split
2a/2b; the switch is a Developer tools toggle, not a setting; with it on the AI does all
of red's buying (Juan keeps red's auto-buying running); the AI gets notes saved with the
campaign.

**Changed 2026-10-10 (DM call): the switch is a setting.** `outside_ai_plans_red` sits on
Campaign Management > HQ automation, so the new game wizard's Campaign options page and
the Settings window both show it. The Developer tools tick box is gone; Copy AI connect
link stays there. An old save's `Game.opfor_ai_enabled` moves into the setting on load.

## Stage 2a: who plans red

- **Toggle off** (default): nothing changes. Writes answer 403.
- **Toggle on**: the write routes open. `Coalition.initialize_turn` plans and buys for red
  exactly as with the toggle off, so the AI starts each turn from the scripted plan and
  keeps it, changes it or clears it. Red's runway and SAM repairs (§68) ride on
  `plan_procurement` and keep running.
- **Take Off** (`QTopPanel.launch_mission`): when the toggle is on and red has no
  packages, `service.run_fallback_if_needed` runs `red.plan_missions` and logs a line.
- Any mid-turn `Game.initialize_turn(for_red=True)` replaces red's ATO, the AI's included,
  with a fresh scripted plan. The briefing tells the AI to re-read `/packages`.

**Changed 2026-10-10 (DM call).** As first built, the toggle stood red's `plan_missions`
and `plan_procurement` down. On the first live use (Kola, turn 1) a Time & Weather re-roll
after ticking the box cleared red's 7 scripted packages and refunded its orders with
nothing planned in their place; a turn later red still had no packages and 610 unspent.
The DM's calls: the scripted planner runs before Take Off; it buys too; the Take Off
re-plan fires only when red has no packages, so it never overwrites an AI's plan. The AI
cancels an aircraft order with `sell/aircraft`; it has no route to cancel a ground order.

## What the first live reviews changed (2026-10-10)

Two reviews of the Kola campaign through the link found the link itself misreporting:

- `/packages` listed each flight's planned loadout as CLSIDs. With
  `restrict_weapons_by_date` on, the mission builder swaps or drops weapons at
  generation, so a 1985 Su-24 read as carrying Kh-31A and Kh-59M and flew with Kh-29L and
  Kh-29T. `views._flight_loadout` now applies `degrade_for_date` exactly as
  `FlightGroupConfigurator.setup_payload` does, and reports weapon names.
- `/validate` called the scripted planner's own plan not OK. A later package lengthens a
  field's runway queue (§104), which pushes an earlier package's start a minute or two
  before the turn clock; the early mission start covers that, and the check did not know.
  `planner.tot_shortfall` now allows `EARLY_START_CAP`, and the package is a note.
  The first fix left ASAP support (the first BARCAP wave, AWACS, tankers) with no
  allowance, and a Kola BARCAP timed before Banak's queue grew still failed the plan.
  `retime_asap_support` re-runs those TOTs at Take Off, so the check now skips them.
- A TOT after `desired_player_mission_duration` was a failure. On a map with 300 NM legs
  every scripted raid is late by that measure. It is a note (DM call).
- `/prev_turns` served the campaign log as written for blue. `views.name_the_sides`
  rewrites "we", "our", "ally", "enemy" and "OPFOR" to Blue and Red. "friendly" is left:
  `ControlPoint.capture_equipment` uses it for whichever side owns the base.

## The map's routes are keyed (2026-10-11)

As first built, only the AI's routes needed the token. The map's own routes
(`GET /flights/` and the rest) were open on the same port, so "blue's ATO is never
served" held for the AI's routes alone, and `/docs` listed every route.

- Every router in `game/server/app.py` now carries a key check. `/docs` and `/redoc`
  are off; `/openapi.json` needs the AI's key.
- The map's key is not the AI's. One shared key would have let the AI's own token read
  `/flights/`.
- The client sends the key as a header from axios and RTK Query, and as `?token=`
  where a header cannot go: map tiles, the websocket and the plain `fetch` calls
  (`withToken` in `client/src/api/backend.ts`).
- `TokenRedactingFilter` keeps `token=` values out of uvicorn's request log.
- **A stale client build leaves the map's routes open.** `client/build` is untracked
  and never rebuilt on launch, so a source checkout can run a bundle from before the
  key; refusing it would blank the map. `ApiKeyManager.check_map_client` looks for
  `X-API-Key` in the bundle at start and, when it is missing, opens the map's routes
  for that run and logs a warning. The release build always ships a matching bundle.
  The AI's routes are never opened this way.
- Flown in an offscreen `QWebEngineView` against the real server on 2026-10-11: the
  rebuilt client loads the game, the tiles list and the saved points with 200s and
  opens the event stream; a wrong key gets 403 on all of them; the pre-key bundle
  gets its map through the fallback.
- Tests: `tests/server/test_api_key_on_every_route.py` calls every route through the
  app with no key and with the AI's key; `tests/agent/test_blue_plan_never_served.py`
  does the same on a real campaign and scans the answers for blue's flight ids.

## What the 2026-10-11 audit changed

The write path had no test on a real campaign; four of these fell out of the first one
(`tests/agent/test_write_on_real_campaign.py`).

- `buy/ground` was refused unless the enemy buy/sell cheat was ticked.
  `GroundUnitPurchaseAdapter(opfor_planner=True)` lets this caller buy for red; the UI
  never passes it.
- A plan that raised anything but a `PlanningError` (OCA or Air Assault at red's own
  base) left its flights holding aircraft and pilots in no package. `planner._plan`
  removes every flight the failed call added to the flight database.
- A task is checked against `target.mission_types` before planning, as the player's
  package dialog does. A flight with `escort` set is exempt.
- Deleting a package sent the map an empty event: the event is now built before the
  package is emptied.
- A buy or sale that stops part way answers `ok: true` and says how many went through.
  A quantity below 1 is refused.
- Writes are refused once the game loop has started (Take Off, or the human running the
  sim clock). The lock between the AI's writes and the UI is still stage 3.
- `parking_free` is served for red's own bases only: it counts aircraft on order.
- `turn_context` reads the verdict with `check_win_loss(announce=False)`, so a read no
  longer posts the victory line.
- The AI's notes are capped at 64,000 characters (`service.NOTES_MAX_CHARS`).
- Only a missing campaign answers 409; another `RuntimeError` is a 500.
- Loss causes on a turn a base is captured: `Sitrep` passes `tally` the owner each
  captured base had during the mission, because it is written after captures commit.

## Source and licence

Ported from `juanjux/dcs-escalation` (`game/agent/`, `game/server/retributionai/`), LGPL-3
like this tree, so code may be copied with credit; each ported file names its source. His
design docs are `ai-docs/00`-`07` in that repo. Read
[retlab-juanjux-fork-watch-notes.md](retlab-juanjux-fork-watch-notes.md) for how he uses it.

What was left out, because RetLab has no such system: pilot morale, leave and crews, High
Command, rebuild countdowns, the derived IADS state (`state_map`), per-package rationale,
air-assault "remain", and his per-campaign token (we use the per-process key). His
`stored_context` is our `Game.opfor_ai_notes`.
Cruise-missile stock is left out because reading it seeds the magazines (a write).

## Shape

- `game/agent/views.py`: pydantic read models, pure functions over a `Game`.
- `game/agent/service.py`: the one layer every transport calls. `opfor_only` refuses any
  side but red there, not in a router, so a second transport cannot forget it.
- `game/agent/mapimage.py`: a Pillow schematic of the same views; no tiles, no network.
- `resources/agent/start.md`, `howtoplay.md`: the AI's briefings. Ours, not Juan's: his
  playbook (122 KB) teaches a commander; ours teaches a reviewer what a finding is.
- `game/server/retributionai/routes.py`: REST shims. Mounted in `game/server/app.py`.
- `game/server/security.py`: every route on the server needs a key, as `X-API-Key` or
  `?token=`. There are two. `ApiKeyManager.KEY` is the AI's (Copy AI connect link) and
  opens `/retribution-ai/*` and `/openapi.json` only. `ApiKeyManager.MAP_KEY` is the map
  page's, passed by `QLiberationMap` as `&key=` beside `server=`, and opens the map's
  own routes and the event stream. See *The map's routes are keyed* below.
- `game/agent/planner.py`, `schemas.py`: the write path over `PackageFulfiller` and the
  purchase adapters. `ProposedFlight.preferred_squadron` (read by
  `AirWing.best_squadrons_for`) is the one engine change: a named squadron, and only it,
  fills the flight; Juan found a type alone let a sister squadron take its place.
- `game/settings/fields/campaignmanagement.py`: `outside_ai_plans_red`.
  `game/game.py`: `opfor_ai_notes` (saved), and `__setstate__` moves an old save's
  `opfor_ai_enabled` into the setting.
- `game/coalition.py`: no branch since 2026-10-10; a §109 comment in `initialize_turn`
  marks where red is still planned with the toggle on. The toggle's gates are in
  `game/agent/service.py` (`_writable_game`, `run_fallback_if_needed`).
- `qt_ui/windows/QLiberationWindow.py`: Developer tools > Copy AI connect link.
  `qt_ui/widgets/QTopPanel.py`: the Take Off fallback.
- Tests: `tests/agent/test_read_api.py`, `tests/agent/test_write_api.py`,
  `tests/agent/test_write_on_real_campaign.py` (the write path on a real campaign), and
  `tests/agent/test_blue_plan_never_served.py`, which scans every GET route's response on a
  real campaign for blue's plan.
- `game/losscauses.py`: last turn's losses by cause, from the killer the base plugin
  records in `S_EVENT_KILL`. Kept on `Sitrep.loss_causes`, served on `prev_turns`.

## Constraints

- Red only. Blue's ATO is the human's private side of the board; Juan closed the same hole
  in his commit `a9d5c5be`. Everything else about blue is served as ground truth, because
  that is what red's scripted planner reads.
- Reads never mutate. Anything that seeds or caches game state stays out of a read.
- Writes need the toggle on and the mission not started, both checked in
  `service._writable_game`.
- The AI plans through the engine's own planners and purchase adapters, never by building
  flights or waypoints itself, so its plan is one the scripted planner could have made.
- The server binds `::1`. The link is for an AI on the same PC; a web AI needs a tunnel,
  which is stage 3's problem.
- The token is per process: the link dies when Retribution closes. So does the map's
  key; a browser on the dev server needs `&key=` in its URL (`client/README.md`).
- Keep `howtoplay.md` true to the engine. When a report turns out to misread a rule, add
  the rule to the briefing's last section.
