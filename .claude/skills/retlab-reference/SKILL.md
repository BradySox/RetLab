---
name: retlab-reference
description: Reference and rules for the RetLab fork of DCS Retribution — the fork's own architecture and verification discipline, upstream project conventions, and Brady's document standards. Use this skill whenever the conversation involves DCS Retribution, the RetLab fork, Liberation, campaign generator code, FlightType additions, Lua plugins or emitters, pull requests or branches for Retribution, wiki pages, mission briefings, change documents, or any DCS development/documentation task — even if the user doesn't name the fork explicitly. When in doubt on a DCS topic, consult this skill.
---

# RetLab Reference

Keeps DCS Retribution work aligned with **two** grains: upstream's project conventions, and
the fork's own hard-won architecture. The biggest failure mode this prevents is doing work
against either grain — proposing something upstream will reject, or proposing something the
fork already tried, flew, and rejected.

**`CLAUDE.md` in the repo root is the live map and always outranks this file.** This skill
carries the *stable* rules; CLAUDE.md carries current state. When they disagree, CLAUDE.md wins
and this file should be corrected.

---

## The Three Places (never confuse these)

GitHub work always involves three separate places. Name which one you mean, every time:

| Place | What it is | Plain English |
|---|---|---|
| **Upstream** | `github.com/dcs-retribution/dcs-retribution` | The official project. Brady doesn't own it. Changes get there only by pull request (a formal "please accept my change" submission). |
| **The fork (RetLab)** | `github.com/BradySox/RetLab` | Brady's own copy on GitHub. He can push anything here freely. Built on upstream's `dev` branch. |
| **The local checkout** | `C:\Users\brady\Desktop\414th-Joint-Fighter-Group\414Ret` | The folder on Brady's PC where editing actually happens. Changes here are invisible to GitHub until pushed. |

Work flows: edit **local** → push to **fork** → (if contributing back) open a PR from the PR
fork to **upstream `dev`**.

Two gotchas that bite every session:
- `gh pr create` needs an explicit `--head`, or it resolves the wrong owner.
- Sessions usually run in a **git worktree** under `.claude/worktrees/`, not the main
  checkout. Validate with the main checkout's venv by absolute path, `cd`'d into the worktree.

When explaining any git operation, say which place it touches and use plain language first,
jargon second: "push (send your saved changes from your PC up to your fork on GitHub)".

---

## Rule 1: Check the grain before designing

Before proposing any new feature, integration, or workflow, check how it is **already done** —
in that order:

1. **The fork.** Read the matching `§N` section of `docs/dev/retlab-features.md` and the design
   note in `docs/dev/design/`. Many ideas have already been built, flown, and *deliberately
   rejected*; the notes say why. Proposing a rejected design back is the most expensive mistake
   available here.
2. **Upstream.** Read `references/upstream-rules.md`. If a design conflicts with an upstream
   convention, flag the conflict explicitly and propose the with-the-grain alternative first.
3. **The wiki spec.** Upstream's wiki carries specs the code implements exactly (e.g. the
   Custom-campaigns "Unit Type Quick Reference" block table). A fork behaviour that differs may
   be a deliberate *deviation*, not a bug — check before "fixing" it or carving it upstream.

---

## Rule 2: Branch and PR discipline

- All upstream PRs target the `dev` branch. **Never** propose a PR against `main`.
- New work starts on a fresh branch cut from `dev`.
- **One PR = one feature/bugfix/change.** Small PRs get reviewed faster, and testers can't
  isolate a bug inside a big mixed PR.
- User-visible features and fixes need a changelog note. Skip for refactors with no
  visible behaviour change and for bugs that never shipped. In RetLab the note is a new
  file in `changelog.d/`, never an edit to `changelog.md`; an upstream carve edits
  upstream's `changelog.md` as usual.
- **Upstream PRs open as drafts** by default; un-draft only on an explicit call.
- Fork PRs are **squash-merged** (sync merges excepted). Never merge unbidden.

The **upstream PR freeze** and its exceptions are in `CLAUDE.md`, *Upstream PRs — standing
rules*. Only the DM lifts it.

---

## Rule 3: Code quality gates

- The gates and the three local commands to run before every push are in
  `docs/dev/CLAUDE-ci.md` (Black over the whole tree, mypy over `game` and `tests`, pytest).
- `qt_ui` is **not** CI type-checked, so anything landed there needs an **in-app eyeball**, not
  just green tests.
- After pulling updates, the client rebuilds in CI — a local `npm run build` is only needed to
  *see* React changes locally.

---

## Rule 4: The fork's architecture — Python plans, Lua executes

The fork runs ~30 Lua plugins deliberately. The standard is the *split*, not the absence of Lua.

**The split.** Python decides; Lua executes. A feature with both halves keeps setup, targeting,
safety and consequence in Python, and only runtime behaviour in Lua. Don't move planning logic
into a plugin, or runtime logic into the planner.

**The four rules that make the split safe** — these are load-bearing and have each been paid for
with a flown failure:

1. **No phantom spawns.** Anything a plugin puts in the world must be a real, tracked unit from
   the real force model, so its loss records natively at debrief. A plugin **owns no kills** and
   invents no units. (Cost of learning: §35 and §37 were both reworked off `coalition.addGroup`.)
2. **Safety is decided in Python as a positive list.** The emitter enumerates exactly what the
   plugin may touch; the plugin cannot widen it. This bounds the blast radius of the
   least-testable layer with the most-testable one. (First stated by §59, removed 2026-09-23.)
3. **Movement only.** A mover feature relocates things; the *consequence* stays in the
   turn-boundary force model. A mover that gets shot down just stops being routed.
4. **One emitter, one entry point.** Each `game/missiongenerator/*luadata.py` exposes exactly
   one `populate_*` function and emits nothing when the feature has no work — no node ⇒ the
   plugin no-ops. Every emitter follows this; keep it that way.

**Plugin mechanics.** A plugin is a folder under `resources/plugins/` with a `plugin.json`,
registered in `resources/plugins/plugins.json` (field table in `references/upstream-rules.md`).
Two traps, both flown:
- **An unticked plugin silently kills its setting.** Any campaign that preseeds a feature must
  preseed its plugin too (the §36 lesson).
- **Lua is 5.1, vanilla DCS units only, definition order matters.**

If a design genuinely needs standalone Lua outside this system, stop and flag it.

---

## Rule 5: Verification discipline

The fork's verification model is **falsification, not confirmation**, and it is the reason its
findings are trustworthy. Preserve it:

- Every runtime feature gets a checklist row (`python tools/claim_id.py row` writes its own
  file in `docs/dev/checklist-rows/`) with an
  **observable pass criterion** and the **fail signature to watch for**.
- ☑ VERIFIED means *"I watched for the fail signature in DCS and it did not occur"* — with a
  date and ideally a Tacview. **Never mark it on a hunch, and never from passing tests.**
- Tests and headless probes cannot promote a row. The desk-adjudicable layer is already
  exhausted; outstanding rows are gated on cockpit time, not more analysis.
- Write the checklist row **the same turn** the finding lands, with the session id — flown
  results get clobbered otherwise.
- **A flown finding should become an invariant, not just a fix.** The pattern that works:
  root-cause → fix → guard test pinning the *class* → audit the rest of the tree for the same
  shape. (§49's immobile hardware became unit data + a lockstep test; §81's serialization drop
  became a test + an AST audit of all 16 emitters.)
- **Prefer a loud failure to a silent one.** A gate that declines silently makes its feature
  unfalsifiable — the reason §21's recovery surge sat undiagnosed. New early-returns should log
  why they declined.

**Standing debt to be aware of:** the fork carries a large backlog of built-but-unflown features
(see the checklist header counts). Adding another unflown gated feature is a real cost. Say so
when it applies.

---

## Rule 6: Document standards

- **Change documents, not direct edits**: for formatting-sensitive files (PowerPoint especially),
  produce a change document describing edits for Brady to apply himself. Never modify directly.
- **Wiki/PR content**: Markdown, ready to paste.
- **Reference material**: clean, table-first Word documents.
- **Mission briefings**: follow the `TheFinalOption_MissionHandoff.docx` template — numbered
  sections, table-first, DCS editor naming conventions, phased build checklists with checkboxes,
  military brevity.
- **Keep the doc faces in sync**, in the order `CLAUDE.md` lists under *Keeping docs in sync*.
- Full formatting detail in `references/doc-standards.md`.

---

## Rule 7: Explain GitHub in plain terms

Brady has asked for GitHub concepts to be dumbed down. Give the plain-English meaning inline the
first time a git/GitHub concept appears in a conversation, anchored to the Three Places table.
Never assume the fork/upstream/local distinction is obvious. **DCS terminology is never dumbed
down; GitHub terminology always is.**

Decisions go through the **AskUserQuestion widget**, not a typed 1/2/3 list — recommended option
first, marked "(Recommended)", each with its trade-off.

---

## Fork facts (RetLab)

| Fact | Detail |
|---|---|
| Fork feature layer | `game/retlab/` — turn-model features, hooked from `finish_turn` / `initialize_turn` / `plan_missions` |
| Custom flight types | `TARPS` (photo-recon; finds hidden enemy command posts) · `JAMMING` (C-130J standoff EW) · `CSAR` (upstream #929's rescue) |
| Squadron script stack | separate repo: `tyfoultz/414th-Joint-Fighter-Group`, `bradys-changes` branch |

The tech stack, CI gates, release rules and the **removed, do not restore** table are in
`CLAUDE.md`; they are not repeated here.

---

## Reference files (read the relevant one before working)

| File | Covers | Read it when |
|---|---|---|
| `references/upstream-rules.md` | Dev setup, branches, PR workflow, black/mypy gates, Lua plugin system | Any Retribution coding, PR, or branch task |
| `references/campaign-design.md` | Campaign YAML, squadron config, .miz placeholder units table, supply routes, IADS, income tables, motorpools | Designing or editing any campaign |
| `references/factions-squadrons-loadouts.md` | Faction format, variant naming, squadron YAML, pilot mechanics, loadout naming + fallback chain | Factions, squadrons, pilots, or loadouts |
| `references/gameplay-mechanics.md` | Packages/TOT/waypoints, task types, stances, frontline math, capture, transfers, auto-purchase | Explaining mechanics or making design decisions that depend on them |
| `references/settings-guide.md` | Settings map, plugin list, performance doctrine, forced_options.lua, kneeboards, modded-unit process | Settings, performance, plugins, advanced config |
| `references/doc-standards.md` | Document formatting standards with examples | Producing any deliverable document |

Fork-side, the deeper territory is in the repo, not here:
`docs/dev/retlab-features.md` (per-feature internals) · `docs/dev/design/` (the design notes,
read before touching the matching code) · `docs/dev/retlab-ingame-pass-checklist.md` (the
verification tracker; settled rows are in its `-archive.md`) · `docs/wiki/` (the mirrored upstream wiki with **RetLab:** delta notes).

---

## Getting the full, current upstream wiki

The reference files are distilled and stable. When exact current detail is needed, clone the
live wiki — one command, always current, all pages as plain markdown:

```
git clone --depth 1 https://github.com/dcs-retribution/dcs-retribution.wiki.git
```

The wiki warns pages can be stale; upstream `dev` code is the final authority — especially
`game/version.py` (campaign format versions), `game/config.py` (income), and
`game/settings/settings.py` (setting names). `docs/wiki/` in this repo mirrors the adopted pages
with the fork's deltas annotated.

---

## Local machine paths

| What | Path |
|---|---|
| Retribution local checkout | `C:\Users\brady\Desktop\414th-Joint-Fighter-Group\414Ret` |
| Squadron scripts/missions repo | `C:\Users\brady\Desktop\414th-Joint-Fighter-Group` |
| DCS install | `E:\DCS World` |
| DCS manuals | `E:\DCS World\Doc` |
| Campaign inspiration goldmine | `E:\DCS World\Mods\campaigns` |
| Hardened pydcs mod exporter | `C:\Users\brady\dcs-export\pydcs_export.lua` |
