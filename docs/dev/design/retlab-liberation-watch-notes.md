# DCS Liberation watch

The grandparent project, still developed. Moved out of `CLAUDE.md` on 2026-10-08, which now
carries only the one-paragraph summary; the text below is as it stood there, so counts and
dates are as of 2026-08-07 unless marked.

## DCS Liberation — the grandparent project, still alive (WATCH, established 2026-08-07)


Retribution forked from `dcs-liberation/dcs_liberation`, and **Liberation did not stop** — it is
actively developed on branch `develop` (792 stars; **15.0.0 released 2026-06-19**, 14.1.0 in
February, commits landing weekly). Do **not** treat it as an archive of pre-fork history. It is a
second upstream: a parallel evolution of the same codebase, with no shared PR flow and no
obligation in either direction. We take from it; we do not carve to it (upstreaming means
`dcs-retribution/dcs-retribution` — see `main-retribution-means-upstream`).

**The watch:** skim Liberation's release notes when a new version drops (`gh api
repos/dcs-liberation/dcs_liberation/releases`). Their notes are terse and tagged by area
(`[Engine]` / `[Campaign]` / `[Data]` / `[UI]`), so a pass costs minutes. Look for **`[Data]`
first** — data lands cleanly in the fork with no code change and no freeze implications, whereas
their engine/UI work usually collides with fork features that already solve the same problem.

Adopted so far:

| Date | Taken | Notes |
|---|---|---|
| 2026-08-07 | 12 hand-measured aircraft `fuel:` blocks (their 14.1.0 + earlier) | Coverage 22 → 40 aircraft types. Checklist **S7**; features doc §46. |

Checked and **already covered** — do not re-investigate without new evidence: carrier/LHA
auto-targeting, front-line spawn exclusion zones, weapons-by-date gating, turn-less mode. Their
auto-purchase model is **behind** ours (they document a fixed 30-unit front-line threshold; we have
`frontline_reserves_factor` / `reserves_procurement_target`). Genuinely open, not yet pursued:
campaign-designer control of on-road vs off-road front-line travel (15.0.0 — set on the supply
route's M-113 waypoints; we hardcode `PointAction.OnRoad` in `convoygenerator.py` +
`flotgenerator.py`), which would fit the driveable-corridor standard.

**Their docs are worth reading too.** Liberation publishes a Sphinx site at
https://dcs-liberation.readthedocs.io — and its **source is in our tree**, inherited through the
fork (`docs/*.rst`, `docs/conf.py`, `.readthedocs.yaml`). Nothing builds it here and it is stale
(`docs/index.rst` still titles the site "DCS Liberation"; `docs/game/index.rst` is an empty
toctree), but the content is live: `docs/modding/layouts.rst` is the authoritative writeup of the
layout system (`layout.miz` + `layout.yaml`, one group per unit type, the `layouts.p` pickle and
*Developer Tools → Import Layouts*), and `docs/modding/fuel-consumption-measurement.md` is the
procedure for measuring the ~217 airframes that still have no `fuel:` block.
