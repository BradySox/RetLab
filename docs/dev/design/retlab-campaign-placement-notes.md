# Campaign unit placement — `tools/campaign_placement.py`

Built 2026-11-07. A shared placer for campaign build tools, and a check of any `.miz`
against the ground as DCS reads it. Checklist row B316.

## Why

The DM moved most of what the build tools placed. Measured 2026-11-07 against his Mission
Editor saves, from the PR heads of #1316 (Red Bear 1985), #1377 (Fulda Gap 1985) and #1447
(Northern Shield 1988):

| | Red Bear | Fulda Gap | Northern Shield |
|---|---|---|---|
| Units he moved | 24 | 11 | 43 |
| Median move | 2.4 km | 2.4 km | 2.9 km |
| Largest move | 15.6 km (Bagram EWR) | 4.7 km | 10.6 km |
| Heading-only fixes | 0 | 0 | 0 |

Three causes:

1. **One ring for every job.** Each tool's `Placer.ring` took the first clear bearing at a
   fixed radius, so nearly every base unit sat exactly 3.0 km (3.4 km at Northern Shield)
   from its field. He spread them by job: depots, ammo and factories in to 1-2 km, guns and
   SHORAD on the approaches, EWRs out to high ground.
2. **The landmap knows land from water and nothing else.** Slope, roads and buildings
   exist only inside DCS.
3. **Town nodes at guessed coordinates.** IADS comms towers, power and HQs placed at a
   town's rough lat/lon landed up to 10 km from where he put them.

## How it works

- **Jobs** (`Job`): DEPOT (ring 600-1,800 m), GARRISON (1,500-2,700 m, inside the 3 km
  capture zone), AIR_DEFENSE (under both approaches of each runway, 800-2,400 m past the
  runway end, up to 1,000 m either side; picks spread across the ends), EWR (1 km grid
  2-12 km out, highest ground first), TOWN (100 m grid within 1,500 m; prefers a spot with
  a building inside 60 m), SPOT (as close to a named point as good ground allows).
- **Separation** between picks by job (`SEPARATION_M`): EWRs 2 km apart, air defense
  900 m.
- **Runway strip and stands** are dropped in Python (`airfield_problem`, the same band and
  stand radius as New Game's `game/theater/airfieldclearance.py`).
- **The ground** is read by `resources/plugins/base/dcs_placement_probe.lua` in a check
  mission (`write_check_mission`): height, steepest tilt over 10 m and 25 m radii, the
  worst surface within 15 m (water, runway, road), and scenery within 60 m. It writes
  `Saved Games\DCS\Logs\retlab_placement_<name>.txt`; needs the de-sanitized
  `MissionScripting.lua`, like the terrain height probe.
- **Flags**: slope over 5 degrees (an erecting launcher never raises past it: the Bavar
  TEL finding, 2026-09-30), water, road, runway or taxiway, a building within 30 m.
- **Cache**: every reading is kept in `Saved Games\DCS\RetLab placement\<terrain>.json`
  (override with `RETLAB_PLACEMENT_CACHE`), so a rebuild needs DCS only for new spots.
- **Review map**: a Leaflet page over satellite imagery, flagged units listed and red.

## Using it from a build tool

```python
from tools.campaign_placement import Job, NeedsCheck, Placer, placement_markers, write_review_map

placer = Placer(mission.terrain, "eastern_reach", on_land=lambda x, y: theater.is_on_land(Point(x, y, mission.terrain)))
placer.request("Jask-Ammo", Job.DEPOT, field.position.x, field.position.y, airport=field)
placer.request("Jask-AAA-1", Job.AIR_DEFENSE, field.position.x, field.position.y, airport=field)
try:
    picks = placer.resolve()
except NeedsCheck as check:
    raise SystemExit(str(check))  # the DM runs the check mission once, then rebuild
```

A pick with `x is None` found no good ground in reach; the review map lists it. A FIXED
site (§122) or a drawn template site is never placed by this: it stays as drawn.

## Open

- Trees: DCS scripting most likely does not return trees from `world.searchObjects`. The
  first run on a wooded map settles it; the readings record the nearest object's type.
- A town node lands near buildings, not on a named one; snapping to a specific scenery
  building is not built.
