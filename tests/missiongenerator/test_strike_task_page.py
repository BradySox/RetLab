from game.missiongenerator import f15ecc
from game.missiongenerator.kneeboard import StrikeTaskPage


def test_target_description_non_f15e_returns_display_name() -> None:
    assert StrikeTaskPage._target_description("SCUD1", 0, False) == "SCUD1"


def test_target_description_f15e_appends_cc_mission() -> None:
    assert StrikeTaskPage._target_description("SCUD1", 0, True) == "SCUD1 (CC 1/1)"


def test_target_description_f15e_reflects_rename() -> None:
    # The CC reference is built from display_name, so a renamed target reads "SCUD1",
    # not the long auto pretty_name.
    assert StrikeTaskPage._target_description("SCUD1", 1, True) == "SCUD1 (CC 1/2)"


def test_target_description_f15e_ninth_target_opens_set_two() -> None:
    # 8 missions a set, so index 8 is set 2 mission 1 (NOT 1/9).
    assert StrikeTaskPage._target_description("Tgt", 8, True) == "Tgt (CC 2/1)"
    assert StrikeTaskPage._target_description("Tgt", 9, True) == "Tgt (CC 2/2)"


def test_target_description_f15e_past_forty_has_no_cc_label() -> None:
    # The jet holds 40 missions; the .miz writer programs none past that.
    assert StrikeTaskPage._target_description("Tgt", 39, True) == "Tgt (CC 5/8)"
    assert StrikeTaskPage._target_description("Tgt", 40, True) == "Tgt"


def test_cc_mission_limits() -> None:
    assert f15ecc.cc_mission(0) == (1, 1)
    assert f15ecc.cc_mission(39) == (5, 8)
    assert f15ecc.cc_mission(40) is None
    assert f15ecc.cc_mission(-1) is None


def test_custom_targets_start_a_set_the_planned_targets_do_not_use() -> None:
    # The old fixed set 2 collided with planned targets 9-16.
    assert f15ecc.next_free_set_index(0) == 8
    assert f15ecc.next_free_set_index(8) == 8
    assert f15ecc.next_free_set_index(9) == 16
    assert f15ecc.cc_mission(f15ecc.next_free_set_index(12)) == (3, 1)
