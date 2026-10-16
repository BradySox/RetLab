# AI fills an empty player flight (§113)

Built 2026-10-16, not flown (row B234). Brady's idea, from his Northern Front 2003 campaign,
where the same pattern is built by hand in the .miz.

## What it does

A player flight marked **AI fills if no player** gets a second, late-activated group: an AI
copy of its player seats, the **twin**. A few minutes into the mission the `aifill` plugin
looks for a player in the client group. If nobody is in any seat, it announces the takeover
and activates the twin at the flight's planned takeoff time (or at once if that has passed).
The package keeps its shape however many people show up.

## Brady's calls (2026-10-16)

| Choice | Call |
|---|---|
| Twin start | Air start over the home base at the planned takeoff time |
| Check time | 5 minutes after mission start (setting, 1 to 30) |
| Announcement | On: a 20-second coalition message (setting) |
| Where it lives | A per-flight box on the General tab, plus a setting that sets every box's starting value |
| Part-player flights | The twin replaces only the player seats; the flight's AI wingmen fly as usual |

Rejected starts: a runway start (a late-activated runway start lands on a taxiway in
multiplayer, `flightgroupspawner.py` `_generate_at_airfield`), and a late parking spawn (the
twin would hold its own parking spots all mission).

## How it is built

- **The rule** (`game/retlab/ai_fill.py`): a flight with player seats, no cargo, and not one
  of `NO_AI_FILL_TASKS` (transport, air assault, ferry, tanker, AEW&C, recovery tanker, TARPS,
  CSAR, the C-130J jammer). `Flight.ai_fills_if_empty` is `None` until the box is touched,
  and `None` follows the *AI fills empty player flights* setting.
- **The twin** (`game/missiongenerator/aircraft/aitwin.py`, called from
  `AircraftGenerator._spawn_ai_twin`): `ai_twin_view` makes the real Flight look like an AI
  air start of its player seats (a roster of `AiTwinSeat`s, `StartType.IN_FLIGHT`, a
  `WaitingForStart` at the takeoff time) and the stock spawner, configurator and waypoint
  generator build it. The view puts the roster, start type, state, group id and the
  waypoint TOTs and fuel back afterwards: the waypoint generator writes those onto the
  shared flight-plan waypoints, and the client flight's kneeboard reads them.
- The twin is named `AI <client group name>` (the first `|` field still ends in the task),
  takes the player seats' callsigns, board numbers and radio, and maps in the `UnitMap` to the
  same pilots. `WaypointGenerator(activation_by_script=True)` writes no activation trigger.
- **The launch** (`resources/plugins/aifill/aifill-config.lua`, always on, no checkbox): reads
  `dcsRetribution.aiFill`, built by `populate_ai_fill_lua`.
- **The briefing**: the client flight's `FlightData.ai_fill` adds an OPTIONAL line to the
  kneeboard BLUF and "(optional, AI fills if empty)" to the English mission briefing.

## Debrief

Only one group of a pair flies. An empty client slot never spawns, so it records no loss and
no §91 sortie record. The twin's losses land on the pilots of the seats it replaced. With
*Player pilots cannot be killed* on (the default) those pilots come back. The twin's sorties
fold into those pilots' campaign careers (§96) like any AI sortie; §97's lifetime profiles
take only human-flown records.

## Known limits

- A player who slots in after the check is not stopped: a mission script cannot block a slot.
  The client group and the twin would then both fly.
- Whether the AI wingmen of a part-player flight spawn and fly with an empty lead seat is
  DCS's call, unverified (row B234).
- The twin is activated at max(check time, takeoff), so a takeoff before the check launches
  the twin late against its timed waypoints.
- French and Chinese briefing templates are unchanged.
