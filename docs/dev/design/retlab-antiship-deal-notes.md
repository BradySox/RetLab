# Anti-ship flights are dealt across the ships of a sea group

**Status:** built 2026-10-11 (DM call the same day). Always on, no setting, both sides.
Not flown yet: row **B219**.

## The problem

`AntiShipIngressBuilder` gave every anti-ship flight the same task list: `AttackGroup` on
each DCS group of the target, weapons `All`. With `AttackGroup` the AI picks one ship of the
group at a time on its own. An anti-ship missile flies for 8 to 10 minutes from 80 NM, so a
flight's whole load is in the air before the first round lands, and every flight in the
mission had the same first target.

A carrier's sea group is two DCS groups: the carrier alone, then its escorts. The carrier's
group was listed first, so everything went at the carrier.

## The run that showed it (2026-10-11)

Caucasus, Vectron's Claw turn 1, run at acceleration with no player, 82 minutes of mission
time. Read from the Tacview and the archived `.miz`.

- Target: Kuznetsov (own group) with Pyotr Velikiy, a Krivak and two Grishas (escort group).
- Blue: 7 F/A-18C flights (24 jets, 4 AGM-84D each) in one package on the carrier's control
  point, and 4 B-52H (16 AGM-84D each) in a second package on the ship group. 160 Harpoons.
- 128 were fired at the Kuznetsov, 32 at Pyotr Velikiy, none at the other three ships.
- The first 56 at the Kuznetsov arrived 8 to 16 at a time. One got through.
- Both capital ships sank at minute 78, as a wave of about 29 reached the Kuznetsov and 26
  of 32 reached Pyotr Velikiy.
- About 40 Harpoons reached the Kuznetsov after it had sunk, or were still flying at it
  when the mission ended. The Krivak and both Grishas were never attacked.
- The B-52s fired half their load at the first group and half at the second, so `expend=All`
  is not literally all for a 16-missile aircraft.

Caveat on "32 together got through": by then the group had already engaged about 100
missiles and may have been short of SAMs.

## What DCS allows

- `AttackUnit` names one ship. The mission can give each flight a different ship.
- A task on a unit that is already dead ends at once, so a list of `AttackUnit` tasks is
  worked down in order. Not yet confirmed in a flown test for ships (B219).
- A missile in flight cannot be retargeted, and flights do not coordinate. The spread has to
  be decided when the mission is built.

## The rule (`game/missiongenerator/aircraft/antishipdeal.py`)

1. **The line.** Living ships of the sea group, in this order: the escort with the
   longest-reach SAM (`threat_range`), then each carrier, then the remaining ships by SAM
   reach. With no SAM on any escort, carriers lead.
2. **Flights per ship.** The top SAM ship and each carrier take 2 flights. Every other ship
   takes 1. Extra flights start again from the top of the line.
3. **Across the whole ATO.** Every anti-ship flight of the coalition whose target resolves
   to the same sea group is dealt in one pass, ordered by package time over target and then
   ATO order. A package on the carrier's control point and a package on its ship group are
   the same sea group.
4. **Fallback.** Each flight's task list starts at its own ship and runs on down the line,
   wrapping. The old `AttackGroup` tasks follow, for whatever is still afloat.
5. A cargo ship (one hull, its own DCS group) is not dealt; it keeps `AttackGroup`.

Tasks are written per ordnance class as before (anti-ship missiles, guided, unguided), so a
flight on the Strike fallback loadout is dealt too.

## Choices and why

- **Two on a capital ship before one on an escort (DM, option 1b).** The auto-planner's
  package is two flights (`PlanAntiShip.propose_flights`). Two Hornet flights carry 32
  Harpoons; split 16 and 16 they arrive in the size that was shot down in the run.
- **The SAM ship first (DM, option 2a).** It is what shoots the missiles down.
- **By whole flights, not by missile count.** A B-52 flight carries 64 Harpoons against a
  Hornet flight's 16, so its ship gets more. Counting missiles needs per-weapon data the
  loadout does not expose cleanly. Revisit if the test flight shows a problem.
- **Both sides (DM, option 3a).** Red's anti-ship flights spread across blue's escorts.
- **No runtime script.** DCS skips a dead unit's task on its own.

## Not addressed here

- The seven Hornet flights shared one TOT and fired over 12 minutes. Arriving together is
  what got missiles through; launch timing is its own piece of work.
- §108's flight report card grades an anti-ship flight on reaching 5 NM from where the ship
  started. A Harpoon shooter fires from 80 NM at a ship that has steamed 28 NM.
- Player flights are dealt a ship like any other, but nothing tells the pilot which one.
