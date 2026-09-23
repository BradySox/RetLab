"""Mission generation: the later mission-generation page."""

from dataclasses import dataclass
from typing import TYPE_CHECKING


from ..booleanoption import boolean_option
from ..boundedintoption import bounded_int_option

if TYPE_CHECKING:
    pass
from ..layout import GENERAL_SECTION, MISSION_GENERATION_PAGE


@dataclass
class MissionGenerationSettings:
    dtc_data_cartridges: bool = boolean_option(
        "Pre-load DTC data cartridges (F/A-18C, F-16C, F-14B(U), AH-64D)",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Embed a native DCS Data Transfer Cartridge for every blue client "
            "Hornet, Viper, F-14B(U) and Apache flight. It loads at spawn unless "
            "the flight's DTC tab says the pilot loads it. "
            "Hornet: the route with "
            "push times, recovery TACAN/ICLS/ACLS, the bullseye as the A/A "
            "waypoint, and the SA page -- front line, your own orbit, the "
            "tankers and AWACS, the known enemy SAM rings. Viper: the route with "
            "TOS, the same picture on the HSD, and the recovery fields as "
            "Destinations with the enemy field you are working over beside the "
            "divert. F-14B(U): references and the front line, the route on plan "
            "2, pre-planned JDAM aimpoints, and the package in the TIS list. "
            "Apache: the route on route ALPHA, the front line and known SAM sites "
            "on the TSD, and a box on the tanker. "
            "Radio presets and the route reach every jet through the mission "
            "anyway, so turning this off costs only the extras. Threat rings "
            "respect recon fog: only sites your map shows exactly. The cartridge "
            "travels inside the .miz, so multiplayer clients get it with the "
            "mission download and do nothing in the jet."
        ),
    )
    mission_briefing_popup: bool = boolean_option(
        "Mission-start briefing popup",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "When a pilot slots into an aircraft, show a short on-screen card -- "
            "campaign, mission number, date, mission time, callsign, aircraft, task, "
            "and departure field -- the way the professional DCS campaigns greet you "
            "at mission start. Fires at mission start in single-player and whenever a "
            "pilot slots in or rejoins on a server. Display only: no gameplay change. "
            "Card duration and the startup grace are options on the 'Mission-start "
            "briefing popup' plugin."
        ),
    )
    host_red_scramble: bool = boolean_option(
        "Host tool: F10 red-interceptor scramble menu",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "A game-master lever for multiplayer events: the mission carries cold "
            "clone templates of the enemy's fighters, and an F10 'HOST: Red Scramble' "
            "menu can launch a 2/4-ship from any red airfield and vector it straight "
            "onto the nearest friendly fighters -- the emergency 'give the flight "
            "something to shoot' button for a session gone quiet. Restrict who sees "
            "the menu with the 'Host red scramble' plugin's 'Host player names' option: "
            "comma-separated DCS names or name fragments (substring match, so a "
            "static tag like 'Flash' covers 'Viper 1-1 | Flash' whatever the flight "
            "prefix); empty shows it to every BLUE client. "
            "Spawned bandits are free and untracked by design -- killing them "
            "changes nothing at the turn boundary; they are event content only."
        ),
    )
    neutral_border_defense: bool = boolean_option(
        "Neutral-faction border defense",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Every nation on the map is drawn with its real border, and one "
            "that is not in the war defends its own airspace with surface-to-"
            "air batteries. They stand inside the border from the moment the "
            "mission starts, so you can find them before you cross. Both what "
            "it fields and how many scale with the country, and what it fields "
            "also follows the era: a legacy campaign sees SA-2, SA-3 and SA-5, "
            "a modern one SA-10 and SA-11, with Rapier, Hawk and Patriot for "
            "the nations that field western kit. A small country gets a single "
            "short-ranged battery, a large one several long-ranged ones, "
            "spread along the stretch of frontier the war is near, each set "
            "back well short of what its missile claims, so the border sits "
            "inside the envelope with margin. Enter and it "
            "warns you by radio at once. Stay past the engage timer or release "
            "a weapon inside the border, and the whole country changes sides "
            "and engages -- not just the site you flew past. Whose airspace it "
            "is, and whether it lets you through, are read from who holds the "
            "airfields inside it. AI intruders are never engaged, and the "
            "auto-planner ignores the borders entirely. Needs the 'Neutral "
            "border defense' Lua plugin ticked. Borders ship with the eight "
            "real-world terrains, so no campaign has to author anything; a "
            "campaign may still author its own. Batteries are free, untracked "
            "event content."
        ),
    )
    civilian_air_traffic: bool = boolean_option(
        "Civilian background air traffic",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Neutral civilian aircraft (airliners, freighters, light props and "
            "helicopters) fly multi-leg milk runs between uncontrolled rear-area "
            "airfields for ambient life. They keep ~40 NM clear of the front line "
            "but NOT of deep BVR/intercept corridors, so a campaign whose air war "
            "reaches far behind the lines may want this off: an IL-76 at altitude "
            "is indistinguishable from a military transport on radar (the flown "
            "Red Tide M1 lost a neutral airliner to a long-range Phoenix shot)."
        ),
    )
    ambient_supply_convoys: bool = boolean_option(
        "Ambient supply convoys (both sides' roads have traffic)",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Every turn, each side's supply-convoy flow is topped up to a small "
            "randomized number of real columns on its own road network -- some "
            "sharing a road, some on different ones -- so there is always traffic "
            "to protect, hunt, and see. The columns are real, tracked units riding "
            "the engine's own convoy system: enemy ones are ordinary Armed Recon/"
            "BAI targets, friendly ones are subject to the convoy-ambush roll, and "
            "every loss counts at debrief. A side with no road between two of its "
            "own bases (island maps) simply gets none."
        ),
    )
    convoy_ambush: bool = boolean_option(
        "Friendly convoy ambushes (support your convoys)",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Your own supply convoys run the roads behind the lines, and sometimes -- "
            "it is a chance, never a certainty -- hidden enemy ambush teams dig in "
            "along the route: one contact, or a gauntlet of five or six down the same "
            "road. Nothing is telegraphed: the convoy looks like any other friendly "
            "convoy and no objective or escort package appears in the UI -- the first "
            "sign is the TROOPS IN CONTACT call when an ambush springs, and supporting "
            "the column (or not) is your call. Left unsupported, an ambushed convoy is "
            "ground down and the supplies never arrive. The convoy and the ambushers "
            "are real, tracked units -- both sides' losses count."
        ),
    )
    cruise_missile_strikes: bool = boolean_option(
        "Ship-launched cruise missile strikes",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Warships that carry land-attack cruise missiles (the Burke's "
            "Tomahawks, the CurrentHill Kalibr ships) can fire them at shore "
            "targets: an F10 'Cruise Missile Strike' menu calls a salvo onto your "
            "last map marker from the nearest ship with missiles left. Each ship "
            "group carries a finite campaign magazine -- there is no rearm, so "
            "every salvo spends stock you never get back. The missiles are real "
            "weapons from a real, tracked ship: kills count at debrief, enemy "
            "point defense can intercept them, and sinking the shooter ends the "
            "raids. Symmetric. Runs via the 'Cruise missile strikes' Lua plugin "
            "-- keep that plugin enabled or this setting does nothing."
        ),
    )
    cruise_missile_auto_raids: bool = boolean_option(
        "Auto-plan cruise missile raids",
        enabled_when="cruise_missile_strikes",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Each turn, a side with a cruise-missile ship in range commits one "
            "raid: a salvo fired early in the mission at its highest-value "
            "reachable enemy ground object -- command centers and comms first, "
            "then war-industry buildings, then anything strikeable. Your own "
            "raids never pick a target hidden from your map, or one in a region "
            "set to Ignore. Watch for the LAUNCH WARNING: "
            "an enemy raid is your point-defense SAMs' problem -- or yours."
        ),
    )
    cargo_ship_convoys: bool = boolean_option(
        "Sea supply convoys (multiple cargo ships per shipment)",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "A ground-unit shipment that travels by sea -- a shipping lane between two "
            "friendly ports with no road link -- sails as a small CONVOY of cargo "
            "ships instead of one lone hull (about one ship per two units, up to "
            "'Maximum cargo ships per sea convoy' on the Mission Generation page). "
            "Each ship carries its own share of the cargo, so losses are "
            "proportional: sink two of five ships and roughly two-fifths of the "
            "reinforcement never arrives, the rest still lands. Turn it off for the "
            "old single-ship behavior."
        ),
    )
    cargo_ship_convoy_max: int = bounded_int_option(
        "Maximum cargo ships per sea convoy",
        enabled_when="cargo_ship_convoys",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=5,
        min=1,
        max=12,
        detail=(
            "The most cargo ships a single sea shipment spreads across. A small "
            "shipment uses fewer; a large one is capped here so a convoy never grows "
            "unbounded."
        ),
    )
    naval_weapon_release_stagger: bool = boolean_option(
        "Stagger naval weapons release",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Warships start the mission on return-fire and are released to "
            "weapons-free one group at a time across a window, instead of every "
            "hull opening up at once. A modern anti-ship missile out-ranges the "
            "whole theater, so without this the fleets are in range of each other "
            "from the moment the mission loads and the entire naval battle happens "
            "in the first five minutes. They still defend themselves while they "
            "wait -- this delays who shoots first, it does not disarm anyone. "
            "Symmetric. Runs via the 'Naval magazines & weapons release' LUA "
            "plugin -- keep that plugin enabled or this setting does nothing."
        ),
    )
    naval_magazines: bool = boolean_option(
        "Cross-turn naval magazines (anti-ship missiles do not rearm)",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Every warship group carries a finite campaign stock of anti-ship "
            "missiles. A mission is a fresh spawn, so without this a fleet reloads "
            "for free every turn and can empty its tubes again and again; with it, "
            "what a group fires this mission is gone for the rest of the war. A "
            "group that runs dry drops back to return-fire -- winchester, not "
            "disarmed: it still shoots back, it just has no missiles left to open "
            "with. Land-attack cruise missiles are counted separately by their own "
            "setting, so nothing is charged twice. Symmetric. Runs via the 'Naval "
            "magazines & weapons release' Lua plugin -- keep that plugin enabled "
            "or this setting does nothing."
        ),
    )
    coastal_batteries_engage_ships: bool = boolean_option(
        "Coastal batteries engage enemy ships",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Coastal anti-ship missile batteries (Silkworm and the like) are set "
            "weapons-free with an active alarm state so they fire on any enemy ship "
            "that enters range -- including sea-supply convoys running the coast. "
            "Without this they sit passive on DCS AUTO and ignore passing hulls. "
            "Symmetric: both sides' coastal batteries defend their waters. Turn it off "
            "to leave coastal batteries on their default passive state."
        ),
    )
    gps_jamming: bool = boolean_option(
        "GPS jamming (satellite-guided weapons go long)",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Enemy GPS-jamming ground sites deny satellite guidance over an area "
            "around themselves. A JDAM, JSOW, JASSM, SLAM-ER or KAB-*S that flies "
            "into a live jammer's bubble is put down off the aimpoint -- further "
            "off the deeper inside the bubble it was -- so the pass fails and the "
            "target survives. Releasing from outside the bubble does not save the "
            "pass: a weapon aimed at a target inside it still flies in, and still "
            "misses by at least a third of the full miss distance. Laser, TV and IR "
            "weapons are unaffected, so the answer is to change delivery method "
            "or find and kill the jammer (which restores accuracy at once, in the "
            "same mission). Symmetric: a site degrades the other side's weapons "
            "only. Known jamming areas are briefed on the kneeboard, but only once "
            "you have engaged the site. Inert unless a campaign fields a "
            "unit that jams. Runs via the 'GPS jamming' Lua plugin -- keep that "
            "plugin enabled or this setting does nothing."
        ),
    )
