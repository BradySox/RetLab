from game.missiongenerator.luagenerator import carrier_rescue_helo_type


def test_a_cold_war_carrier_flies_a_sea_king_rescue_helo() -> None:
    assert carrier_rescue_helo_type(1985) == "SH-3W"
    assert carrier_rescue_helo_type(1991) == "SH-3W"


def test_a_carrier_from_1992_flies_a_seahawk_rescue_helo() -> None:
    assert carrier_rescue_helo_type(1992) == "SH-60B"
    assert carrier_rescue_helo_type(2020) == "SH-60B"
