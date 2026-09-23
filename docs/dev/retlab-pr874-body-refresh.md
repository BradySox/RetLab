# Upstream #874 — replacement title and PR body

Paste-ready title and description for
[dcs-retribution#874](https://github.com/dcs-retribution/dcs-retribution/pull/874).
The PR grew on 2026-09-23 from carrier comms alone to a Navy pass, on the DM's call: the
fork's §62 board numbers (`afa5d01b`), then the pinned board number and the X00-only CAG
livery rule (`0e1ccf92`), then the Navy-only scope for both (`c8804d0d`). Updating an existing PR is allowed under
the freeze.

Head after the update: `c8804d0d` on `BradySox/dcs-retribution:carrier-comms-curation`, with
upstream `dev` @ `49e8067f` merged in (`568e5930`) and another session's header rewording
(`832b7a72`) merged in. Black, `mypy game tests` and pytest (526 passed) green on that head.

## Title

```
Navy: curated carrier comms, sequenced board numbers, and a pinnable board number
```

## Body

```markdown
Navy fixes in three isolated commits, so each can be reviewed or dropped on its own.

## 1. Curated carrier comms (`b65729ac`)

DCS builds the "CV Operations Data" kneeboard page from the miz. The generator fed it
allocator output: the boat named `0796 | CVN-71 Theodore Roosevelt`, TACAN 1X with a random
ident re-rolled every turn, ICLS 1, Link 4 on a random UHF, a new ATC frequency each mission.

- `game/data/carrier_comms.py`: one plan per hull. TACAN follows the hull number with a boat
  ident (CVN-71 → 71X `TRO`), hull-keyed ICLS, Link 4 in the 336 MHz ACLS band, a stable ATC.
- Values stored on the control point win. Resolved values persist, so they stay put across turns.
- `TacanRegistry.alloc_near`: a hull channel owned by a map beacon (Bagram is 74X on
  Afghanistan) goes to the nearest free channel, not the bottom of the band.
- `alloc_for_band` now marks its pick. The X-band T/R and A/A pools overlap at 37–46 and
  100–126, and neither iterator marked, so one channel could be issued twice.
- `IclsAllocator` replaces `iter(range(1, 21))` so curated and fallback picks share one pool.
  Pretense only changes type; its sequential behavior is unchanged.
- The flagship unit is named by its hull name, set before `UnitMap` registration so debrief
  kill tracking keys off the same string.
- Hulls with no plan (`VINSON`, `Essex`, `hms_invincible`, mod carriers) keep the old allocators.

Tests: `tests/test_carrier_comms.py` (25).

## 2. Squadron-sequenced board numbers (`afa5d01b`)

pydcs gives every aircraft a random `onboard_num` (`set.pop()` over the free pool), so Navy
jets spawn with arbitrary three-digit modexes.

- `ModexAllocator` (`game/missiongenerator/aircraft/modex.py`): each Hornet/Tomcat squadron
  gets a block (100, 200, …, per coalition, Tomcats first). Its jets are numbered X00, X01, X02
  in generation order: tasked flights, then untasked ramp aircraft. The block is reserved with
  the `Country`, so the random allocator cannot hand a number inside it to another jet.
- The Tomcat does not draw `onboard_num`. No F-14 livery declares a board-number material
  (Su-27, MiG-29A, F-15C, Su-25 and FA-18C liveries all do), so the painted number is the livery.
- `LiveryAllocator` replaces the random round-robin during mission generation, which could put
  two CAG birds in one squadron. Commit 3 changes how it picks.
  `Squadron.ordered_livery_set` rejoins `_livery_pool` so a save taken mid-rotation loses no livery.
- Data: each F-14B(U) squadron shipped as two presets (High Vis / Low Vis), each pinning one
  livery, so every jet in a squadron showed the same painted number. They are now one preset per
  squadron with every DCS livery for it, CAG bird first. Task lists are unchanged. F-14B VF-32's
  set now leads with 100.
- Scope is Hornets and Tomcats. Other airframes keep the stock pydcs number. Numbering is per
  mission, not per pilot, so this does not close #863.

Tests: `tests/missiongenerator/test_modex.py` (8), `tests/missiongenerator/test_livery_allocator.py`
(7), `tests/test_squadron_livery_sets.py` (4 checks over the five presets).

Flown in our fork: Hornet numbers checked in the F2 view; the Tomcat CAG-first livery order
checked in the generated miz on three campaigns.

## 3. Pinned board number, and the CAG livery is X00's alone (`0e1ccf92`, `c8804d0d`)

Navy only: both halves apply to the Hornet and Tomcat set that commit 2 numbers. Every other
aircraft is unchanged, including the random round-robin over its livery set.

- Payload tab: **Set board number** pins the lead's number; wingmen follow in order
  (105 → 105, 106, 107, 108). Shown on Hornet and Tomcat flights only. Stored as
  `Flight.board_number`; old saves read None.
- The tab refuses a run that overlaps another flight of the coalition or passes 999, keeps the
  previous value, and names the flight that holds the number (`board_number_conflict`).
- At generation `ModexAllocator` claims pinned numbers per coalition first. The pinned flight
  wears them; squadron sequences skip them; a random pydcs number that lands on one is
  re-rolled; claims are reserved with each `Country`. So no other package wears a pinned number.
- The Tomcat livery follows the jet's board number. A livery painted with that number is used
  where the set has one. A CAG / hi-vis livery (an X00 number, or "CAG" / "Hi Vis" in the name)
  goes to the X00 jet only. Other jets cycle the line liveries.
- Before this, a two-livery set such as F-14B(U) VF-143 put its CAG bird on every second jet.
- The idle ramp path now stamps the number before painting, so the livery can read it.
- A Tomcat pin reaches the paint only where a livery with that number exists; the tab says so.

Tests: the pinned cases in `tests/missiongenerator/test_modex.py` (15 in all), and
`tests/missiongenerator/test_livery_allocator.py` (18 cases). Not flown yet.

## Checks

Black, `mypy game tests`, pytest (526 passed) on current `dev` (`49e8067f`).
```

## Notes for whoever pastes it

- **Pasted 2026-09-23** from a local session (`gh pr edit 874`). The text below is what #874
  now shows; the cloud session that wrote it had no upstream API access.
- `b65729ac` is the carrier-comms commit's short SHA on the PR branch; confirm it with
  `git log --oneline` on the branch if the history was ever rewritten.
