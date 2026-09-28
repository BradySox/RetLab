# WATCH — standing list for the daily fly

**Things to look for in whatever you were flying anyway.** No mission is built for these, no
toggles are flipped, no campaign is required. Five slots, hard cap.

When one closes, note it in the matching checklist row the **same session** with the date
(flown results get clobbered otherwise), move it to [`ARCHIVE.md`](ARCHIVE.md), and pull the
next from the parking lot.

---

## The list

*(Refilled 2026-08-22. Slots 1–2 carried over; 3–4 are new. The previous parking lot was
cleared — both entries named rows that had already closed, `Q3` VERIFIED and the loadout
watch pointing at RETIRED `B42`.)*

### 1 · An AI flight inside a shaded neutral border, and nothing happens — `B121`

**Where:** the F10 map, any campaign with neutral border defense on. **~2 min**, whenever an AI
flight is near a shaded (hostile-neutral) border.

- **Pass:** an AI flight visibly inside the shading draws no hail, no warning and no fire, and
  the country's batteries stay neutral.
- **Fail:** a neutral battery fires at, or the country turns hostile over, an AI aircraft with
  the `engageAi` option off.
- **Why it's here:** pulled from the parking lot 2026-09-27 when `B77` closed on the DM's call.
  No AI stray has crossed a border in three recorded missions, so it closes on the first one.

### 2 · A HARM at a Skynet site: does it go dark, or fight through — `G42`

**Where:** any SEAD fly with the RWR open, or the recording afterwards. **~5 min.**

- **Pass:** a site that cannot shoot a HARM goes dark when one is inbound; a site that can
  (an HQ-7, a Tor) stays up and fires at it.
- **Fail:** a site with no HARM defence keeps radiating until the HARM lands.
- **Why it's here:** pulled from the parking lot 2026-09-23 when `B70` closed on the test 39
  re-read. Test 39's one HARM at a Skynet site went at an HQ-7, which stays live by design. Test 40's
  ARAPAIMA Kub survived seven HARMs because its paired Tor killed them all, so whether the
  Kub itself went dark is still open.

### 3 · The planner behaviour bar actually switches the suite — `B54`

**Where:** the settings UI, Campaign Doctrine. **~1 min.** App-side.

- **Pass:** moving the bar changes the planner options underneath it, and a turn planned after
  the change reads differently from one planned before.
- **Fail:** the bar moves and nothing beneath it changes.
- **Why it's here:** pulled from the parking lot 2026-09-16 when `B78` closed on the DM's call.

### 4 · BMP-3s in a front fight fire single aimed shots — `B103`

**Where:** any front with BMP-3 groups and TIC on (Iron Gate, Caucasus 2026, Red Tide), from
the cockpit or the F10 map. **~2 min** of watching one firefight.

- **Pass:** a BMP-3 group fires single aimed shots, visibly slower than the BTRs beside it.
- **Fail:** BMP-3s fire at the infantry salvo rate, as fast as the BTRs.
- **Why it's here:** pulled from the parking lot 2026-09-27 when `B111` closed on the DM's call.
  A recording does not carry per-round gunfire, so this needs eyes.

### 5 · A stuck TIC unit names itself, and the retries are spread — `B108`

**Where:** `dcs.log` after any mission with a front line, one grep for `stuck`. **~1 min.**

- **Pass:** each stuck line names its unit, and the retries are spread across many units
  rather than one unit retrying hundreds of times.
- **Fail:** unnamed stuck lines, or one unit holding most of the count.
- **Why it's here:** pulled from the parking lot 2026-09-16 when `B90` closed on the DM's call.
  Test 33 had a live front and no stuck line at all, so it is still unflown.

---

## Parking lot (pull one when a slot frees)

| Row | Watch for | Note |
|---|---|---|
| *(empty since 2026-09-27: `B121` and `B103` were pulled into slots 1 and 4)* | | |

Closed and dropped items, with the reasoning: [`ARCHIVE.md`](ARCHIVE.md).
Contrived-condition tests live on [`LOCAL.md`](LOCAL.md).
How to write an item, and the three-cadence model:
[`retlab-verification-cadence-notes.md`](../design/retlab-verification-cadence-notes.md).
