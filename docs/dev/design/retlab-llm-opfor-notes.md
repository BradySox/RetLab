# Outside AI for red: read and report first, commander later · §109

**Status:** stage 1 (read and report) built 2026-10-09, not flown (row B201). Stages 2 and
3 agreed, not started.

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
| 2 | Write actions (packages, buys, stances, transfers, ship moves, repairs), behind a setting that is off by default. The scripted planner fills red at Take Off when the AI has not planned | Agreed, not started |
| 3 | MCP at `/mcp` for the claude.ai app; the toolbar activity icon and the Take Off lock while the AI works | Agreed, not started |

DM's answers on 2026-10-09: port Juan's code (2a); red sees blue as the scripted planner
does, never blue's ATO (4a); the old planner fills in if the AI does not finish (5a).

## Source and licence

Ported from `juanjux/dcs-escalation` (`game/agent/`, `game/server/retributionai/`), LGPL-3
like this tree, so code may be copied with credit; each ported file names its source. His
design docs are `ai-docs/00`-`07` in that repo. Read
[retlab-juanjux-fork-watch-notes.md](retlab-juanjux-fork-watch-notes.md) for how he uses it.

What was left out of his reads, because RetLab has no such system: pilot morale and leave,
High Command, rebuild countdowns, the derived IADS state (`state_map`), `stored_context`
(it needs a save field; stage 2), and his per-campaign token (we use the per-process key).
Cruise-missile stock is left out because reading it seeds the magazines (a write).

## Shape

- `game/agent/views.py`: pydantic read models, pure functions over a `Game`.
- `game/agent/service.py`: the one layer every transport calls. `opfor_only` refuses any
  side but red there, not in a router, so a second transport cannot forget it.
- `game/agent/mapimage.py`: a Pillow schematic of the same views; no tiles, no network.
- `game/agent/docs/start.md`, `howtoplay.md`: the AI's briefings. Ours, not Juan's: his
  playbook (122 KB) teaches a commander; ours teaches a reviewer what a finding is.
- `game/server/retributionai/routes.py`: REST shims. Mounted in `game/server/app.py`.
- `game/server/security.py`: `ApiKeyManager.verify` accepts `X-API-Key` or `?token=`.
  Only the AI routes depend on it; the map server's own routes stay open, as before.
- `qt_ui/windows/QLiberationWindow.py`: Developer tools > Copy AI connect link.
- Tests: `tests/agent/test_read_api.py`.

## Constraints

- Red only. Blue's ATO is the human's private side of the board; Juan closed the same hole
  in his commit `a9d5c5be`. Everything else about blue is served as ground truth, because
  that is what red's scripted planner reads.
- Reads never mutate. Anything that seeds or caches game state stays out of a read.
- The server binds `::1`. The link is for an AI on the same PC; a web AI needs a tunnel,
  which is stage 3's problem.
- The token is per process: the link dies when Retribution closes.
- Keep `howtoplay.md` true to the engine. When a report turns out to misread a rule, add
  the rule to the briefing's last section.
