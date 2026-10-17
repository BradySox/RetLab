# Sector war

Status: **step 1 built 2026-10-12** (territory and sectors drawn, row B229), plus
**battles along the border** (row B230). Steps 2 and 3 agreed, not built. Features doc §111.

## Where it came from

A Reddit screenshot of a DCS F10 map (Caucasus, the Sukhumi front) filled each side's whole
territory, orange-brown for red and blue-grey for blue, with the front as the edge between
them. A second set showed hand-drawn "BATTLE MAP" CAS kneeboard cards built per named sector
(WHISKEY-14 attack, XRAY-3 defence). The script behind the map was not identified.

## Brady's choices (2026-10-12, decision cards)

| Question | Answer |
|---|---|
| Drawing only, or a sector war | Full sector war |
| How deep | Sectors decide the fight; ground units still live at their bases |
| Sector shape | Shaped by the ground, not a square grid |
| Sector size | About 10 NM |
| Base capture | A base falls with its sector |
| Which games | New games, setting on by default (step 2) |
| Sectors a won battle takes | Scaled by the win: strong 2, clear 1, minor 1 only when the winner attacked |
| Mission captures (Air Assault, troops in the base zone) | Kept; the base's sector goes with it |
| A supply road cut by enemy sectors | Carries no convoys, so the base it served loses road supply |

## Build steps

| Step | What | Rules change |
|---|---|---|
| 1 | Sectors made and named; territory drawn on the F10 map and the app map, worked out from today's bases and fronts | No |
| 2 | Battles take sectors; a front sits on the sector edge; a base falls with its sector; supply runs through your own sectors | Yes, new-game setting, on by default |
| 3 | A CAS battle-map kneeboard card per front | No |
| 4 | Ground units live in sectors (its own call; not agreed) | Yes |

## Step 1: how it works

`game/theater/sectors.py`.

- **The war region** is every §98 country holding a base on either side, out to its
  border, plus the land within 60 NM of the outermost land bases. It is clipped to the
  landmap's inclusion zones, minus the sea and minus any §98 country holding no base on
  either side. Off-map spawns and ships are not land bases. On a map with no border data
  (Germany) the 60 NM box is the whole region. Until 2026-10-12 the box was the region
  everywhere, and on Iraq it drew as a plain rectangle with most of the country unfilled.
  A campaign that authors its own §98 borders lists its neighbours only (COIN has no
  Afghanistan zone), so a country holding a base is also read from the map's own file in
  `resources/borders/`.
- **The grid** is 1 NM cells. A cell costs 1 to cross on drivable ground and 4
  (`MAX_TERRAIN_DIFFICULTY`, §90 rung D) inside an exclusion zone.
- **Sectors** grow from seeds by multi-source shortest path over that grid, so an edge
  settles where the driving cost from two seeds is equal: along ridges and around rough
  ground. Every land base seeds its own sector. The rest are one per 10 NM square, jittered
  by up to 35% of the spacing with a random generator seeded by the square, so the same
  campaign always gets the same sectors. Without the jitter, open ground grew plain squares.
- **Names** are a phonetic row counted from the north and a column counted from the west,
  per 10 NM square: WHISKEY-14. Past 26 rows the words repeat with a lap number
  (CHARLIE2-35). Two seeds in one square get a letter (WHISKEY-14B).
- **Territory** uses the same growth with two labels. Sources are each side's land bases,
  the convoy route on each side of the front's position, and the front's bowed trace (§90
  rung E) offset 1.2 NM to each side. That pins the border to the front line already drawn
  on the F10 map.
- **Shapes** are the cells joined row by row, smoothed by a one-cell close and open,
  clipped to the coast (simplified to 250 m), then simplified as one coverage so the two
  sides share a single edge. Islets under 2 NM² are not drawn.
- **Sector ownership** for display is whoever holds most of a sector's cells.

Built on demand and cached: the sectors while the bases stay put, the territory while no
base changes hands and no front moves. Measured on Brady's PC with whole countries in the
region, sectors plus territory: Abchazian Blitz 0.4 s, Red Tide 1.3 s, Iraq Desert Storm
1.0 s, Northern Flank 1.3 s, Anatolian Reach 0.7 s. The sector edges for the app map take
0.9 s on Red Tide, once.

### F10 map

`DrawingsGenerator.generate_territory`, first, so every other drawing sits on top. Blue
layer. A DCS drawing has no holes, so a territory with a pocket inside it is cut into
pieces through the pocket (`hole_free_pieces`); the edge is drawn as separate closed lines
so the cuts do not show. Every drawing gets its own name, because MIST drops a repeated one.

### App map

`/game` carries `territory` (each side's polygons, pockets as holes) and `sectors` (the
edges between sectors as lines, and each sector's name, owner and seed). Layers: Territory
(on by default) and Sectors (a sub-row, off by default; names show from zoom 9).

## Battles along the border

Brady, 2026-10-12: "frontline units spread across the entire shared border so that it feels
like a push instead of one single 10nm front line battle." Two calls on decision cards:

| Question | Answer |
|---|---|
| How units sit along the border | A battle per sector (not an even thin line) |
| How much border a front fills | Up to twice Maximum frontline width (not the whole border). Was one width until 2026-10-13: Sinai left ~200 of a 240 mile border quiet |

Before this, a front's units stood on one straight line across the road between its two
bases, clipped wherever the line met undrivable ground. Measured at turn 0: Red Tide
(Fulda) 2.4 NM, Abchazian Blitz (Sukhumi) 4.3 NM, Iraq Desert Storm (H-3) 43 NM.

`game/theater/frontbattles.py`:

- The shared border is where the two sides' territory shapes meet, merged into lines.
- A front takes the line nearest its position and the stretch of it centred there, as long
  as twice Maximum frontline width (160 km at the 80 km default) measured along the border. Where the line
  ends first, the stretch slides to keep its length.
- The stretch is sampled every quarter mile. A sample counts if it is on drivable ground
  (inclusion zones minus exclusion and sea) and nearer this front than any other front.
- Each sector the counted samples pass through holds one battle, on its longest unbroken
  run, if that run is at least 1 NM. The battle's centre is the run's middle; blue's forward
  heading is the normal to the border that points into red's ground.
- A battle's groups spread along the run, following the border, up to 5 NM.

`FlotGenerator`:

- Picks as many battles as the side with more armor wedges, evenly from end to end
  (2026-10-13, Brady's card "Bigger side sets it"). The fewer-wedges rule made one pocket
  for the whole front when blue had one tank group: Desert Aladeen, 1 battle of 5.
- Deals wedges out across the battles in turn. A side with fewer wedges than battles
  spreads them end to end, one wedge in the middle battle, so some pockets are one-sided.
  A cluster member joins its wedge; artillery and the rest are dealt across the side's
  own battles. Each group then steps back to its depth along its
  own battle's heading, and keeps that heading for every order.
- Measured with a test force on Red Tide: the two sides' spread went from 2.7 NM to 20 NM
  across 3 battles. Iraq: 29 NM to 36 NM. Abchazian Blitz: 1 or 2 battles in the 6 NM of
  drivable coast.

The F10 and app-map front line follows the stretch from the first battle to the last.
Built and cached with the territory; a few milliseconds per front after it.

### CAS on the battle line

Brady, 2026-10-17: a CAS flight's FLOT bounds and its one 10 NM search circle at their middle
never reached battles 25 to 50 miles out. Now (`game/ato/flightplans/cas.py`):

- FLOT START and FLOT END sit on the outer battles, the end nearer the departure first. A
  front with one battle runs the length of that battle's spread.
- Up to 3 BATTLE stops sit between them, each the battle nearest an even spacing along the
  line, so every stop is on a fight. Two battles: no stops.
- The on-station time (CAS duration) is shared across the stop legs by length.
- The map draws a circle of engagement range round each stop instead of a corridor.

DCS tasking: the ingress waypoint carries an *EngageTargetsInZone* on FLOT START; each later
stop carries its own (`CasStopBuilder`). These are en-route tasks: one stays on from its
waypoint to the end of the route, so they stack. pydcs has no "stop at waypoint N" condition.
The sum is a row of tight circles along the border, so the AI may go back to an earlier battle.
Measured on Desert Storm (H-3): five stops about 29 km apart, 115 km end to end.

## What step 1 does not do

- No rule changes. The front still slides along the road between two bases, and the
  battle result is still one result per front, whatever happens in each battle.
- No rivers: the landmap has no river data, so a sector edge follows a river only where
  the river is inside an exclusion zone.
- Sectors are rebuilt from the bases and the landmap, not saved. Step 2 saves only who holds
  each one, by name, so a change to the naming would give a running campaign's renamed
  sectors back to nobody.

## Step 2: sectors decide the fight

Built 2026-10-12. Setting *Sectors decide the ground war*, Campaign features, on for new
games; a save from before it loads with it off (`Game.__setstate__`). Code:
`game/theater/sectorwar.py`.

- **Owners are saved** on `game.sector_war`, by sector name, so a landmap fix that renumbers
  the sectors keeps a running campaign's ground. Turn 0 takes them from the step 1 territory
  (bases plus the fronts as first placed); after that the fronts follow the sectors, never
  the other way round. The territory is drawn from the owners.
- **The front line** sits where its route between the two bases enters red's sectors
  (`FrontLine._sector_war_progress`), clamped 5 km clear of both bases as before. Cached per
  owner change: the property is read many times a turn.
- **A won battle takes sectors** (`MissionResultsProcessor.take_sectors`, after the strength
  change, which still happens). The result itself is unchanged: one per front. Strong win 2,
  clear win 1, minor win 1 only when the winner attacked. Each sector taken is the loser's
  sector nearest the front that touches the winner's ground, within one Maximum frontline
  width of the front (at least 15 NM): half of `battle_stretch_m`, which spans two widths.
  The turn's messages name the sectors.
- **A base falls with its sector** (`commit_sector_war`, after the mission's own captures):
  same capture, prisoners and redeploy as a mission capture. A base taken in the mission
  takes its sector first, so the two never fight. Every turn the base sectors are synced to
  their bases.
- **Supply through your own sectors**: a road link between two friendly bases whose convoy
  route crosses an enemy sector is left out of that side's transit network
  (`road_is_cut`). No convoy drives it, and rung A's supply tiers see the base lose road
  supply. Shipping and airlift links are untouched. Only blue's strength recovers each turn
  (red never has; `ENEMY_BASE_STRENGTH_RECOVERY` is unused upstream), so for red the effect
  is the convoys.

Measured on new games with the recommended sizes: two strong wins in a row took Haina on
Red Tide (Fulda front, 55 NM route); one strong win took Psyrtsha on Abchazian Blitz,
whose sector already touches the border. No road was cut at the start of Abchazian Blitz,
Red Tide or Desert Storm.

## Not checked

- How large filled drawings look and perform on the DCS F10 map. The largest piece is
  Northern Flank's Russia, about 2,700 corners; Red Tide's is about 1,650. Row B229.
