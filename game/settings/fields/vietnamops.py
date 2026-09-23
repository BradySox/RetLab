"""Vietnam Ops: the period mechanics suite."""

from dataclasses import dataclass
from typing import TYPE_CHECKING


from ..booleanoption import boolean_option

if TYPE_CHECKING:
    pass
from ..layout import VIETNAM_OPS_PAGE


@dataclass
class VietnamOpsSettings:
    # Vietnam Ops (period-ops suite) -- opt-in Vietnam-era runtime mechanics. All
    # default OFF globally; the Vietnam campaign YAMLs flip the relevant ones ON via
    # their settings: block. These are SCAFFOLD toggles: each gates a feature that
    # lands on its own branch (see docs/dev/design/retlab-vietnam-ops-notes.md). Until
    # that feature lands, the toggle is inert.
    vietnam_arc_light: bool = boolean_option(
        "Arc Light area bombing (heavy bombers)",
        VIETNAM_OPS_PAGE,
        "Fire support",
        detail=(
            "Heavy-bomber (B-52) Strike missions saturate the target area with a walking "
            "carpet of bombs at time-on-target instead of a single aimpoint, modeling the "
            "Operation Niagara Arc Light strikes. Tactical strikers (F-4/A-4) are unaffected."
        ),
        default=False,
    )
    vietnam_naval_gunfire: bool = boolean_option(
        "Naval gunfire support",
        VIETNAM_OPS_PAGE,
        "Fire support",
        detail=(
            "Offshore gun ships (battleship/cruiser main batteries) deliver call-for-fire "
            "bombardment against coastal targets. Coastal campaigns only -- has no effect "
            "inland (e.g. Khe Sanh), where naval gunfire never reached."
        ),
        default=False,
    )
    vietnam_snake_and_nape: bool = boolean_option(
        "Snake and nape (napalm CAS)",
        VIETNAM_OPS_PAGE,
        "Fire support",
        detail=(
            "An attack aircraft making a low, fast pass over enemy ground lays a wall of "
            "fire across the target -- the iconic Vietnam 'snake and nape' CAS delivery "
            "(retarded bombs + napalm). Rewards flying the run in low and on the deck; "
            "both sides' attack jets get it. Needs an attacker down low over enemy troops, "
            "or it has no effect."
        ),
        default=False,
    )
    vietnam_flak_gauntlet: bool = boolean_option(
        "AAA flak gauntlet",
        VIETNAM_OPS_PAGE,
        "Battlefield & interdiction",
        detail=(
            "Enemy anti-aircraft artillery throws barrage flak bursts and tracer streams "
            "across the target area and thickens against predictable run-in lines, recreating "
            "the AAA-heavy Vietnam threat environment. Atmospheric pressure to jink -- not a "
            "new invisible-SAM lethality model."
        ),
        default=False,
    )
    vietnam_convoy_interdiction: bool = boolean_option(
        "Truck-convoy interdiction",
        VIETNAM_OPS_PAGE,
        "Battlefield & interdiction",
        detail=(
            "Armed Recon missions over enemy road corridors find a moving supply convoy that "
            "scatters and hides when hunted; destroying it dents enemy logistics. Models Ho "
            "Chi Minh Trail / Steel Tiger interdiction."
        ),
        default=False,
    )
    vietnam_super_gaggle: bool = boolean_option(
        "Super Gaggle hilltop resupply",
        VIETNAM_OPS_PAGE,
        "Battlefield & interdiction",
        detail=(
            "A formation of transport helos runs one supply run per turn into a cut-off "
            "forward friendly outpost (launch field -> outpost -> back), tracked live on the "
            "F10 map so you can find it and fly escort -- modeling the Khe Sanh 'Super "
            "Gaggle'. Needs a friendly forward outpost near the front, or it has no effect."
        ),
        default=False,
    )
    vietnam_fac_marking: bool = boolean_option(
        "FAC(A) willie-pete target marking",
        VIETNAM_OPS_PAGE,
        "Battlefield & interdiction",
        detail=(
            "Airborne forward air controllers (OV-10 Broncos loitering near the front) mark "
            "the nearest enemy ground concentration with white-phosphorus smoke AND a named "
            "F10 map mark (e.g. 'BTR-60 x6'), so you can find the target and roll in -- the "
            "iconic Vietnam FAC. Needs a friendly OV-10 airborne over the battle area, or it "
            "has no effect."
        ),
        default=False,
    )
