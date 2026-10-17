import pytest

from game import persistency
from game.armedforces.forcegroup import ForceGroup


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # ForceGroup/layout preset loading reads from the DCS saved-game folder,
    # which is only configured once the app boots. Point it at an empty temp
    # dir so loading falls back to the bundled resources/ presets.
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


_DOG_EAR = 'MCC-SR Sborka "Dog Ear" SR'


def _unit_names(group: ForceGroup) -> set[str]:
    return {unit.variant_id for unit in group.units}


def test_soviet_style_shorad_presets_include_dog_ear() -> None:
    assert _DOG_EAR in _unit_names(ForceGroup.from_preset_group("SA-9 SHORAD"))
    assert _DOG_EAR in _unit_names(ForceGroup.from_preset_group("SA-15 SHORAD"))
    assert _DOG_EAR in _unit_names(ForceGroup.from_preset_group("SA-19 SHORAD"))


def test_non_soviet_shorad_presets_do_not_include_dog_ear() -> None:
    assert _DOG_EAR not in _unit_names(ForceGroup.from_preset_group("Roland"))


def test_sam_sites_do_not_include_dog_ear() -> None:
    # The Sborka is a regimental SHORAD acquisition radar, not part of SA-2/3/5
    # or S-300 site TO&E (and a mid-1980s anachronism at Vietnam-era SA-2 sites),
    # so the SAM-site layouts must not grow a Dog Ear point-defense slot.
    for preset in ("SA-2/S-75", "SA-3/S-125", "SA-5/S-200", "SA-10/S-300PS"):
        assert _DOG_EAR not in _unit_names(ForceGroup.from_preset_group(preset)), preset


@pytest.mark.parametrize("faction_name", ["Iran 2015", "WRL - Task Force Red"])
def test_campaign_sa15_pick_is_not_rejected_for_the_added_dog_ear(
    faction_name: str,
) -> None:
    # These factions field the SA-15 but list no Dog Ear. A campaign's
    # `ground_forces: SA-15 SHORAD` pick was thrown out for the Dog Ear alone and
    # a random SHORAD went in its place (Noisy Cricket Redux, Assault on Damascus).
    from game.factions import FACTIONS

    faction = FACTIONS[faction_name]
    group = ForceGroup.from_preset_group("SA-15 SHORAD")
    assert _DOG_EAR in _unit_names(group)
    assert _DOG_EAR not in {u.variant_id for u in faction.accessible_units}
    assert all(u in faction.accessible_units for u in group.units_a_faction_must_own)
