# Flight report cards (§108)

**Status: BUILT 2026-09-29, not flown.** Row B158.

## What it is

After a mission, the Qt debrief shows one card per blue flight that got airborne.
Human-crewed flights come first. Each card has a grade and the facts behind it.

The grades are Unsat, Below average, Average and Above average.

## Why

- §91 records each aircraft's track, shots, hits, kills and fuel. Before this, only the SITREP's
  one line and the §96 logbook read those records. Nothing judged a flight against its plan.
- Installed single-player campaigns (campaigns B and D) spend most of their scripting on a
  per-mission debrief. It uses an instructor's voice and lists each fault, and one of them shows
  a four-level grade. This is the same idea, built from data a dynamic campaign already has.

## What is graded

| Check | Source | Points |
|---|---|---|
| Timing at the timing point (table below) | the track sample inside the radius nearest the planned time, against `tot_for_waypoint` minus `mission_start_time` | on time within 2.5 min +1; within 5 min 0 (a note); past 5 min −1; never inside the radius −2 |
| Result | one of the three rows below | +1 at most, however it was earned |
|  Package target (attack tasks) | the target TGO's units and scenery in this mission's losses | at least half destroyed +1; some 0; none −1. SEAD: any destroyed +1, none 0 |
|  Ship kills (Anti-ship) | `naval_kills` on the records | any +1 |
|  Ground kills (CAS) | `ground_kills` on the records | any +1 |
| Air kills (fighter tasks) | `air_kills` on the records | any +1 |
| Weapons (Strike, BAI, DEAD, OCA, Armed Recon) | shots and hits | 2 or more released, no hits and no kill −1 |
| Losses | `debriefing.air_losses` | any −1; half the flight or more −2 |
| Fuel on landing (humans only) | `fuel_at_end` of human records seen on the ground after their last airborne sweep, times internal capacity (`fuel_max`) | under the airframe's measured `min_safe` reserve −1 (always shown in lb); no measured reserve: under 15% of internal fuel −1 |

A score of +2 or more is Above average, 0 to +1 is Average, −1 to −2 is Below average, and
below that is Unsat.

## Where timing is measured

| Task | Timing point | Radius |
|---|---|---|
| Strike, BAI, DEAD, SEAD, Anti-ship, OCA, Armed Recon | the ingress point, against the planned ingress time | 12 NM |
| Escort, SEAD Escort | the join point, against the planned join time | 12 NM |
| BARCAP, TARCAP, AEW&C, tanker, jamming | the station (`tot_waypoint`) | 5 NM |
| Everything else | `tot_waypoint` | 5 NM |

- **An attack flight that never enters the radius but released a weapon is not faulted.**
  It fired from range. It gets no timing line.
- **A flight whose planned time is after the mission ended is not graded on timing.** The
  card says "Mission ended before its time on target." Mission end is the latest
  `last_seen` of any record.
- A plan with no `layout.ingress` or `layout.join` (a custom plan) falls back to
  `tot_waypoint`.

Until 2026-10-11 every task was timed within 5 NM of `tot_waypoint`, which for an attack
flight or an escort is the target itself. Test 55 (2026-10-11, 23 graded flights): all 8
anti-ship flights fired Harpoons from about 100 NM and were faulted "Never reached the
target area", as were their 3 escorts. A CAS flight and a SEAD escort due on station
after the mission ended at minute 82 got the same fault. The flight that sank a ship was
graded Below average.

## How a card reads

- Line 1: the task and the package target, with the grade at the right
  (`Anti-ship · Admiral Kuznetsov`, `Unsat`).
- Line 2, dimmed: the squadron and the aircraft (`VFA-103 "Jolly Rogers" · 4 x F/A-18C`),
  and `(player)` for a human-crewed flight.
- Then each fault, then each finding.

Until 2026-10-11 the title was the DCS group name (`Target Task|12|FA-18C_hornet|`).
A flight's callsign is not an option: pydcs assigns it at generation and the campaign
does not keep it. A card pickled before this has no squadron or target, and falls back
to the task alone and the group name.

## Constraints

- **Timing is measured from `mission_start_time`, not `conditions.start_time`.** §104 can start
  the mission up to 30 minutes early, and sortie-record times count from mission start.
- **Arrival is the sample nearest the planned time, not the first.** A flight that takes
  off or holds inside the radius and is still there at the planned time was on time. The
  FROG strike of test 55 took off 5 NM from its ingress point.
- **The 12 NM radius is measured, not chosen.** The AI opens fire on the way in and turns
  away short of the ingress point: 4 of test 55's 7 Hornet flights came no closer than
  9 to 10 NM.
- **Anti-ship and SEAD are never faulted for firing with no hits.** A Harpoon can be shot
  down and a HARM loses a radar that shuts off. A hit is also only counted while the
  mission runs, so weapons still flying at the end count as misses.
- **SEAD is not faulted when the site survives.** Suppression leaves no record to grade.
- **A tanker or AEW&C flight tops out at Average.** It has timing and nothing else to
  score.
- **Early is fine for station tasks** (BARCAP, TARCAP, AEW&C, tanker, jamming). Arriving early
  to a strike is still graded.
- **Fuel is graded only after a landing.** A jet still airborne when the mission ends has no
  landing fuel. The reserve is the airframe's own `min_safe` (Hornet 2,000 lb of 10,803, Viper
  1,000 of 7,163); 34 airframe files carry one. The 15% fallback sits between those two.
- **AI fuel is never graded.** With `ai_unlimited_fuel` on, an AI record's fuel field is
  constant (§91), so it is not a fuel state.
- **The package target counts every kill on it**, whoever made it. The card says "package
  target" for that reason.
- **Gun hits do not count.** §91 counts a hit only against a recorded shot, and DCS raises no
  shot event for a gun.
- **Graded at results commit**, in `MissionResultsProcessor.record_flight_cards`, while the
  flown ATO still exists. The result is stored on `Game.last_flight_cards`.
- **A grade changes nothing in the campaign.** Nothing reads it back. This follows §96's
  rule: a record, never a reward.
- **No setting.** It is always on (§104/§107 precedent).

## Files

- `game/retlab/flight_grades.py`: `FlightFacts`, `grade_flight`, `facts_for`, `flight_cards`.
- `game/sim/missionresultsprocessor.py`: `record_flight_cards`.
- `qt_ui/windows/QDebriefingWindow.py`: `FlightReportCards`, `FlightReportCard`.
- `tests/retlab/test_flight_grades.py`, `tests/qt_ui/test_debriefing_window.py`.

## Deferred

- A kneeboard page with the last mission's cards.
- Grading escorts on their package's losses.
- A CAP that commits on the way to its station and never arrives is still faulted for it
  (test 55: an F-14 flight with one kill, 49 NM short).
- A per-pilot trend in the §96 logbook, such as grades over the last ten sorties.
- Tuning the thresholds after the first flown read (row B158).
