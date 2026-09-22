# My aircraft, saved points and the DTC options (§102)

One window for the seat the player is flying this turn: the aircraft, the points and
drawings they saved for it, its loadout and its data cartridge. The DTC tab is rebuilt per
airframe with real options. Built 2026-09-22. Not flown yet; rows **B135** and **B136**
own the verdicts.

Source of the window and the saved points: juanjux/dcs-escalation, LGPL-3.0, the same
licence as this tree. Credited in file headers and commit messages. The kinds, orbits,
drawings, Tomcat/Apache wiring and the DTC options are ours.

## 1. What it is

- **My aircraft** — a button beside Air Wing. Lists every flight a player sits in. Right
  side, three tabs:
  - **Saved points** — the points table, grouped by kind, plus a drawings list. Rename,
    copy/paste between aircraft, Add (type or paste a position, pick a kind), show on the
    map, delete.
  - **Loadout** — the Edit Flight `QFlightPayloadTab`, unchanged.
  - **DTC** — the Edit Flight `QFlightDtcTab`, rebuilt (§5).
- **The map** — the crosshair button at top left reads any spot. Its popup saves the spot
  as a kind, or starts a drawing. A layer shows every saved point, orbit and drawing.
- Points and drawings live on the **squadron**, not the flight.

## 2. Kinds

| Kind | Counts against | Hornet | Viper | Tomcat | Apache | A-10 |
|---|---|---|---|---|---|---|
| Waypoint | waypoint pool | WYPT, `R2` | NAV_PTS `STPT`, `R2` | plan 3 | WPTHZ, route BRAVO | CDU EXTRA |
| IP | waypoint pool | WYPT (no marker) | `type: IP` | `XIP` code | WPTHZ | CDU |
| Target | waypoint pool | WYPT (no marker) | `type: TGT` | `XST` code | WPTHZ | CDU |
| Hold | waypoint pool | WYPT | `STPT` | plan 3 | WPTHZ | CDU |
| Orbit | orbit pool | `CAP_PTS` entry | HSD box (GEO lines) | plot-line box, plan 3 | TSD area | not offered |

The four point kinds share each jet's waypoint room: Hornet 57, Viper 24, Tomcat 50,
Apache 50, A-10 2050. Orbits: Hornet 6, Viper 3, Tomcat 4, Apache 12. Kinds with no room
are not offered. Nothing takes a markpoint.

**Why the Hornet shows no IP or target marker:** its NAV_PTS has no type field
(`FA-18C/DTC/WYPT/WYPT_NAV.lua:703-727`). The only target marker is the route sequence's
`TGT`, one per sequence (`ROUTE_SEQ.lua:1286-1300`).

## 3. Drawings

| Jet | Where | Room |
|---|---|---|
| Hornet | SA FLOT lines; the boundary gives up lines down to one | 2 × 7 points; areas close by repeating a corner |
| Viper | HSD line sets 2-4, before the support boxes | 15 of the 25 shared points; the boundary keeps 10 |
| Tomcat | plan 3's plot lines, `closed` flag | 4 × 9 points (8 closed); 50 points a plan in all |
| Apache | TSD Lines of 2-4 vertices (longer lines split); a 4-corner area as a TSD Area | 15 lines, 12 areas |

Sources: `FAOR_FLOT.lua:9-11`, `GEO_LINES.lua:586`, `F-14BU_DTC.lua:104-137,164-168`,
`AH-64D/DTC/NAV/Lines.lua:52,241`, `Areas.lua:3,498-501` (the editor's own area shape,
matched exactly). The Apache manual (Dec 2025, p195) lists TSD lines and areas as not
implemented; whether the aircraft draws them today is unverified.

## 4. Where a point ends up, and its number

`game/missiongenerator/dtc/savedpoints.py` answers for the cartridges and the kneeboard,
so the number on the kneeboard is the jet's:

- Hornet, Viper, Apache: after the route (the route's cockpit length, skips removed).
  They write the whole navigation set, so points need the **Flight plan** section on.
- Tomcat: plan 3, numbered from 1; independent of the Flight plan section.
- A-10: his `numbers_for`.
- A point that did not fit prints `-`. An orbit prints `ORB` with heading and length.
  Drawings are listed on the first page by their first corner.

## 5. The DTC tab

- **Per airframe.** Only the sections this jet's cartridge carries
  (`game/missiongenerator/dtc/sections.py`), grouped Navigation / Situation picture /
  Weapons and defence / Comms, each with what it does on this jet.
- **Loading.** Load at spawn (default) or pilot loads it. Hand-load still binds the
  cartridge; it writes `AutoLoad = false` on the unit (`dcs/flyingunit.py:106-121`). This
  is the answer to B28's STBY objection, and campaign G's own choice.
- **Waypoints in the cartridge.** One tick per waypoint type in the plan. An unticked type
  is left out of the Hornet, Viper, Apache and Tomcat route; the numbers after it close up
  and the kneeboard route table prints `-` on its row. Stored as type names, so a re-plan
  keeps the choice.
- **Known SAM sites near the route.** Optional: only sites whose ring comes within N nm of
  the route. Default every known site, as before.
- **Saved points** and **Your drawings** are sections of their own.

## 5a. §74 defects the schema research found — fixed 2026-09-22 (DM call)

Found while mapping §3 against the DCS install; all four fixed on the DM's call the same
day. Each is pinned by a test in `tests/missiongenerator/test_dtc.py`. Not flown: B105
carries the Apache check. The Tomcat change only trims what exceeded the jet's own limit,
so B91 (verified) stands.

1. **Apache lines over 4 vertices** are deleted by the editor (`Lines.lua:52,241,
   1112-1127`); §74 wrote up to 8 plus 5-point boxes. **Now:** the boundary is split
   into 2-4 vertex lines, and each tanker box is a 4-corner TSD area (`Areas.lua`).
2. **Apache route `eta` is per leg**, the first point carrying the start time
   (`Routes.lua:540-549,857-874`); §74 wrote a running total. **Now:** per leg.
3. **Hornet: one `TGT` per route sequence** (`ROUTE_SEQ.lua:1286-1300`); §74 marked every
   target. **Now:** only the first target on the sequence.
4. **Tomcat plans over their limits**: `route_as_line` allows 3 lines, and waypoints,
   line points and references share 50 (`F-14BU_DTC.lua:164-168,2674-2707`, a closed
   line spending one more). **Now:** every plan is fitted: the route is never cut, the
   last references go first (the smallest rings), then the last lines (tanker boxes).

Also noted: Hornet `text_note` is capped at 5 characters by the editor
(`WYPT_NAV.lua:1187`); we write up to 24, for the route and saved points alike.

## 6. Differences from his tree

- **His DTC is not ours.** His `dtc.py` (#342) was not taken; injection targets §74.
- **Capacity lists only what this tree loads.** No CJS Super Hornets.
- **No coordinate-format setting**; degrees and decimal minutes throughout.
- **Show on map pans, it does not zoom** (the existing `reset_on_map_center` event).
- **Not ported:** his #348 Qt half (unit-card coordinates) and his UI restyle
  (`qt_ui/windows/playable/style.py` carries the few controls the window needs).

## 7. The elevation lookup reaches the network

`game/elevation.py` fetches Mapzen terrarium tiles from AWS open data (no key, no
account) to pre-fill a point's elevation. It is the real world's height, not DCS's.
Offline it returns nothing. Only tile indices are sent. His design, kept.

## 8. Constraints — do not undo

- **Points and drawings stay on the squadron** (his #369).
- **One numbering function** for kneeboard and cartridge.
- **Never offer a kind the airframe cannot be handed.**
- **Hornet/Viper/Apache points need the Flight plan section**: those cartridges replace
  the whole navigation set, so saved points alone would erase the route.
- **Skips are stored as waypoint-type names**, never indices — a re-plan rebuilds the
  waypoints.

## 9. Needs an in-game pass

- **B135** — STPT N in the jet is the point the kneeboard numbers N; SEQ1 still the route.
- **B136** — the DTC options: hand-load leaves the cartridge unloaded until selected; a
  skipped type is gone from the jet with the numbers closed up; drawings and orbits show
  on each jet's page.

Headless coverage: `tests/missiongenerator/test_dtc.py` (the §102 block),
`tests/test_dtc_tab.py`, `tests/test_saved_points.py`, `tests/test_a10cdu.py`,
`tests/test_playable_*.py`, the client's `coordinatepicker` suites, and a full headless
generation (Hornet, Viper, Apache, A-10; no save had an F-14B(U)).

## 10. Deferred

- A Tomcat F-14B(U) generation run (unit tests only so far).
- The Hornet `text_note` 5-character cap (§5a, noted only).
- Times on/off per flight; the coordinate-format setting; zoom on Show on map.
