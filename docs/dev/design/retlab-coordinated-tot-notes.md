# Coordinated TOT (§114)

A hand-planned package can time itself behind the SEAD or DEAD package hitting the SAM that
covers its target. It is the default for a package made from the map since 2026-10-16.

## Why

Brady, 2026-10-16: packages made by right-clicking an objective defaulted to ASAP, and more
than half of them "didn't go". Read against test 56 (Iraq, 2026-10-11):

- No launch bug. Both hand-made ASAP packages, PORCUPINE and PIGLET, got airborne.
- Baghdad was jammed for every package there, auto-planned ones included: groups sat 15 to
  30 minutes before takeoff. PIGLET's SEAD Hornets took off at minute 31, after the minute 27
  they were due over the SAM.
- ASAP waits for a package's slowest flight. A helicopter or C-130 in a package can push the
  TOT past the end of the mission (Red Tide's save: a CSAR/TARCAP package at +1:43).

The auto planner already times its own strikes 2 to 8 minutes behind their SEAD (§69), but it
skips ASAP and player packages, so a player package never got that window.

## The rule (Brady's choices, 2026-10-16)

| Choice | Picked |
|---|---|
| Default for a new map package | **Coordinated**. ASAP and a typed TOT stay. Works whatever the planner-suite setting says. |
| What it waits for | **SEAD/DEAD only**: 2 to 8 min after the latest SEAD or DEAD package whose target's ring covers this target, the §69 window (`MissionScheduler.SEAD_WINDOW_LEAD` and `_DURATION`). Fighter cover and same-target spacing were offered and not picked. |
| When it runs | **On every change in the package window, and again at Take Off** for every Coordinated package, so packages added later still count. |
| No cover to time | **ASAP plus a warning line** in the package window. |

- Only strike-class packages wait (`MissionScheduler.COORDINATED_STRIKE_TYPES`: Strike, BAI,
  OCA, CAS). Any other Coordinated package flies ASAP.
- Never earlier than ASAP. A window opening after the mission ends, or closing before the
  package can arrive, leaves it ASAP with a warning.
- A known radar SAM whose ring covers the target and has no SEAD or DEAD package planned
  against it is named in a warning, unless the package brings its own SEAD, SEAD Escort or
  SEAD Sweep flight.
- Recon fog: a site counts only if blue knows it (`known_for`, inside `fog_intact()`), both
  as a window provider and in a warning. Red planning reads ground truth. Neutral sites are
  ignored.

## Files

- `game/commander/coordinatedtot.py`: `plan_coordinated_tot`, `apply_tot_mode`,
  `retime_coordinated_packages`.
- `game/ato/package.py`: `Package.auto_coordinated`; `__setstate__` reads an old save as off.
- `game/sim/missionsimulation.py`: the Take Off pass, before `settle_mission_start` (the TOT
  moves the startups the early start is chosen from).
- `qt_ui/models.py` (`PackageModel.update_tot`, `set_coordinated`),
  `qt_ui/windows/mission/QPackageDialog.py` (the tick, the TOT line, the warning line),
  `qt_ui/windows/mission/QAutoCreateDialog.py` (Auto Create keeps the ticked mode).
- `tests/commander/test_coordinated_tot.py`.

## Not done

- The auto planner's own scheduling is unchanged. It runs at turn start, before the player
  plans, and never sees a Coordinated package.
- The carrier-recovery stagger is not re-run at Take Off for a Coordinated package.
- Not flown. Row B236.
