# Civilian air traffic (§129)

Rebuilt 2026-11-09. The DM asked for a fresh design and said the old rules were wrong.
Features doc §129; in-game pass row B323.

## The DM's picks (2026-11-09)

| Question | Pick |
|---|---|
| Which aircraft | Real civil types only. The IL-76, An-30 and C-130 are gone: they read as military transports on radar, and Red Tide M1 lost an IL-76 to a Phoenix shot. |
| Airliners | The Yak-40 everywhere, plus the An-26 on Caucasus, Kola, Afghanistan and Syria only. The C-47 was offered first and dropped: it ships in the paid WWII Assets Pack (`<DCS>\Mods\tech\WWII Units`), so it is not in base DCS. |
| Timing | A steady stream: about the same number in the air from start to end. |
| Routes | Enter at the map edge or take off from a field neither side uses. Stay 40 NM clear of the front and outside every SAM ring blue knows of. |
| Density | A setting, Off / Light / Normal / Busy, default Light. |

Unchanged: weapon hold, invisible to AI, airline-name callsigns, no traffic on the 1944 maps,
the Vietnam boats.

## How it works

1. `CivilianTrafficGenerator` (`game/missiongenerator/civiliantraffic.py`) plans every flight
   of the mission at generation.
   - Two layers. **Airways**: airliners on long legs (80 NM or more) between map-edge gates and
     civil fields, at FL200 to FL250. **Hops**: light planes and helicopters between civil
     fields 10 to 70 NM apart, low, on radar altitude.
   - The flights flying at mission start (the layer's target) are spawned live. Airliners are
     placed partway along their route at cruise; hops sit on the runway.
   - The rest are late-activated: a map-edge entry air-starts at its gate at cruise, a field
     departure ground-starts on the runway. The queue holds enough flying time to keep the
     target for 4 hours (`COVER_S`), capped at 60 flights a layer.
2. `civtraffic` (`resources/plugins/civtraffic/civtraffic-config.lua`, `skipUI`, always on)
   ticks every 30 s.
   - It removes a flight that landed (after 90 s), reached its map-edge exit (15 km), never
     took off (15 min) or outlived its max age.
   - It then switches queued flights on until each layer is back at its target: at most two a
     tick, and never two from one field within 3 minutes.
   - It only activates and destroys groups; it never spawns one. `Group:destroy()` fires no
     dead event, so removals record nothing.

### War airspace

`war()` unions a 40 NM circle round each front with both sides' air-defense threat rings
(`ThreatZones.for_faction(..., viewer=Player.BLUE)` inside `fog_intact()`), plus a 5 NM margin.
Blue's view, not the truth: a gap in the traffic over an unfound red site would give the site
away. Every leg is a straight line that must not touch it, and a field inside it is never an
end.

### Map-edge gates

Six points per side of the box round every airfield on the map. Not `Terrain.bounds`: it leaves
out real airfields and runs upside down on Syria, Normandy and Persian Gulf.

### Civil fields

Airfields no control point owns, outside the war. Fixed-wing traffic needs a runway (test 59:
an An-26 and an IL-76 sent to Syria's helipads crashed). Nothing ground-starts from a field
above 2,000 m (test 40: an IL-76 out of Bamyan hit the valley).

## Levels

| Level | Airways | Hops |
|---|---|---|
| Off | 0 | 0 |
| Light (default) | 4 | 1 |
| Normal | 6 | 3 |
| Busy | 10 | 4 |

A dry run on two saves (2026-11-09): Mozdok turn 3 (Caucasus) planned 29 flights on Light and
80 on Busy; Baltic Fury turn 3 (GermanyCW) 30 and 79.

## Constraints carried over from flown tests

- pydcs speed arguments are km/h. Passing m/s air-started the 2026-08 fleet below stall.
- A field departure needs a waypoint at its cruise level, or DCS flies a shallow V and never
  climbs (2026-08-08).
- RAT stays retired: it crashed the sim resolving heliport ids (`woCharacterHuman`).

## Era and region data

`game/missiongenerator/civilianfleet.py`. Each type has a first year in civil service; a
campaign before it never sees the type. Liveries are base-DCS folders only (Yak-40 Aeroflot,
Georgian Airlines, Olympic Airways, Ukranian; Mi-8MT Russia_Aeroflot, UTair, Gazprom; UH-1H
the `[Civilian]` set; Christen Eagle registrations). Regions are keyed by `Terrain.name`; an
unknown map falls back to the Soviet sphere.

## Old saves

`civilian_air_traffic` (a checkbox) became `civil_air_traffic` (the level) in
`game/settings/migration.py`: on becomes Light, off stays Off.

## Not built

- Real airways (named routes between real-world fixes).
- Airliners from the free Civil Aircraft Mod; offered and declined 2026-11-09.
- Rerouting a flight already in the air when the war moves; routes are fixed at generation.
