# Trains on drawn rail lines (§123)

Asked for 2026-10-24 from the stock-assets survey: DCS ships 4 locomotives and 12 wagon
types and RetLab used none. DM calls: Fulda Gap 1985 first, both sides run trains, a
destroyed train loses its whole cargo.

## What DCS does (two probes, 2026-10-24)

- A train is one vehicle group with one unit of type `Train`, a `wagons` list (locomotive
  first) and waypoints whose action and type are `On Railroads`. ED's missions also carry
  a `spans` track path; it is not needed.
- pydcs reads a train as a plain vehicle and drops `wagons`; `TrainUnit` writes it back.
- A waypoint 230 ft off the rails snaps onto them. Two trains with no track path ran at
  37 mph for 10 minutes.
- **Scripts see the whole train as one unit**, the locomotive, health 5. Wagons cannot be
  hit or counted on their own.
- **A destroyed train fires no dead event.** Its health went to -745 and its speed to 0,
  and the group still read as alive. Losses are therefore polled
  (`train_losses.lua`), not read from events.

## Choices

- Rail lines are authored in the `.miz`, like supply roads; never a yaml list.
- Rail beats road between the same two bases. A pair has one link type in the transit
  network, so a train and a road convoy never share a transport key.
- The whole cargo is lost with the train. Per-wagon losses were the first pick and are
  impossible (see above).
- Trains ignore **Disable land convoys**: one train is one unit, not a column to path.

## Deferred

- Map styling: a rail line draws as a supply route; it has no look of its own.
- Rail lines for other campaigns (Caucasus, Syria, the other Germany campaigns).
- Fulda Gap: Frankfurt-Schweinfurt and Erfurt-Merseburg need their own probe. In probe 2
  (2026-10-24) a Wurzburg-Schweinfurt train and a Merseburg-Leipzig train both ran
  steadily away from their next station; the other seven lines ran toward theirs.
