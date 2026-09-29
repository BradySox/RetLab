# Flight report cards (§108)

**Status: BUILT 2026-09-29, not flown.** Row B156.

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
| Timing at the TOT waypoint | first track sample within 5 NM, against `tot_for_waypoint` minus `mission_start_time` | on time within 2.5 min +1; within 5 min 0 (a note); past 5 min −1; never inside 5 NM −2 |
| Package target (attack tasks) | the target TGO's units and scenery in this mission's losses | at least half destroyed +1; some 0; none −1 |
| Air kills (fighter tasks) | `air_kills` on the records | any +1 |
| Weapons (attack tasks) | shots and hits | 2 or more released and no hits −1 |
| Losses | `debriefing.air_losses` | any −1; half the flight or more −2 |
| Fuel (humans only) | `fuel_at_end` of surviving human records | under 5% −1; under 15% a note |

A score of +2 or more is Above average, 0 to +1 is Average, −1 to −2 is Below average, and
below that is Unsat.

## Constraints

- **Timing is measured from `mission_start_time`, not `conditions.start_time`.** §104 can start
  the mission up to 30 minutes early, and sortie-record times count from mission start.
- **Early is fine for station tasks** (BARCAP, TARCAP, AEW&C, tanker, jamming). Arriving early
  to a strike is still graded.
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
- `qt_ui/windows/QDebriefingWindow.py`: `FlightReportCards`.
- `tests/retlab/test_flight_grades.py`.

## Deferred

- A kneeboard page with the last mission's cards.
- Grading escorts on their package's losses, and CAS on front-line kills.
- A per-pilot trend in the §96 logbook, such as grades over the last ten sorties.
- Tuning the thresholds after the first flown read (row B156).
