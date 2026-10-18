# WATCH — standing list for the daily fly

**Things to look for in whatever you were flying anyway.** No mission is built for these, no
toggles are flipped, no campaign is required. Five slots, hard cap.

When one closes, note it in the matching checklist row the **same session** with the date
(flown results get clobbered otherwise), move it to [`ARCHIVE.md`](ARCHIVE.md), and pull the
next from the parking lot.

---

## The list

*(Slot 1 refilled 2026-10-18 with `B251` when `B121` closed. Refilled 2026-08-22. Slots 1–2 carried over; 3–4 are new. The previous parking lot was
cleared — both entries named rows that had already closed, `Q3` VERIFIED and the loadout
watch pointing at RETIRED `B42`. Slots 4 and 5 (`B103`, `B108`) went 2026-10-15 with TIC.)*

### 1 · A raid draws a few alert jets, not the whole reserve — `B251`

**Where:** any mission where a big package goes into enemy airspace with QRA on, or the
recording afterwards. **~5 min.**

- **Pass:** each raid draws 1 to 4 enemy alert jets at a time; alert squadrons far from
  any raid keep their jets on the ground.
- **Fail:** 5 or more alert jets go after one raid at once, or a base with no raid near it
  empties.
- **Why it's here:** pulled in 2026-10-18 when `B121` closed on test 62. Test 62 is why the
  cap exists: red launched 32 alert jets from 10 squadrons in 15 minutes (#1302).

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

---

## Parking lot (pull one when a slot frees)

| Row | Watch for | Note |
|---|---|---|
| *(empty since 2026-09-27: `B121` and `B103` were pulled into slots 1 and 4)* | | |

Closed and dropped items, with the reasoning: [`ARCHIVE.md`](ARCHIVE.md).
Contrived-condition tests live on [`LOCAL.md`](LOCAL.md).
How to write an item, and the three-cadence model:
[`retlab-verification-cadence-notes.md`](../design/retlab-verification-cadence-notes.md).
