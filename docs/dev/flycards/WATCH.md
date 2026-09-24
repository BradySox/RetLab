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

### 1 · The ramp time you are given matches the airframe you are starting — `B77`

**Where:** the mission-start briefing card and the kneeboard, any flight. **~1 min.** App-side.

- **Pass:** a Tomcat and a Viper starting cold get different allowances, each the airframe's own.
- **Fail:** every airframe gets the same number.
- **Why it's here:** pulled from the parking lot 2026-09-16 when `B48` closed on the DM's call.

### 2 · A HARM at a Skynet site: does it go dark, or fight through — `G42`

**Where:** any SEAD fly with the RWR open, or the recording afterwards. **~5 min.**

- **Pass:** a site that cannot shoot a HARM goes dark when one is inbound; a site that can
  (an HQ-7, a Tor) stays up and fires at it.
- **Fail:** a site with no HARM defence keeps radiating until the HARM lands.
- **Why it's here:** pulled from the parking lot 2026-09-23 when `B70` closed on the test 39
  re-read. Test 39's one HARM at a Skynet site went at an HQ-7, which stays live by design.

### 3 · The planner behaviour bar actually switches the suite — `B54`

**Where:** the settings UI, Campaign Doctrine. **~1 min.** App-side.

- **Pass:** moving the bar changes the planner options underneath it, and a turn planned after
  the change reads differently from one planned before.
- **Fail:** the bar moves and nothing beneath it changes.
- **Why it's here:** pulled from the parking lot 2026-09-16 when `B78` closed on the DM's call.

### 4 · A striker and its escort hold one pace after the join — `B111`

**Where:** F10 after the join, before the ingress: ground speed **and altitude** for the
striker and each escort. **~5 min**, on a flight you were flying anyway.

- **Pass:** the escort reads within ~15 kt of its striker at the same altitude.
- **Fail:** a 20–50 kt gap, which is what test 32 measured and what one authored airframe
  (the Hornet at M0.78) among unauthored ones produces. Record the loadout with each number;
  the readings are what unblocks `cruise_mach:` for the other airframes.
- **Why it's here:** pulled from the parking lot 2026-09-16 when `B79` closed on the audit.

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
| `B121` | An AI flight visibly inside a shaded neutral border, and nothing happens | F10 map on any campaign with `neutral_border_defense` on; no stray in three missions so far |
| `B103` | A BMP-3 group in a front fight firing single aimed shots, slower than the BTRs beside it | Iron Gate and Caucasus 2026 field them on the front; the rate is not in a recording |

Closed and dropped items, with the reasoning: [`ARCHIVE.md`](ARCHIVE.md).
Contrived-condition tests live on [`LOCAL.md`](LOCAL.md).
How to write an item, and the three-cadence model:
[`retlab-verification-cadence-notes.md`](../design/retlab-verification-cadence-notes.md).
