"""Night flights get goggles where they add to the cockpit and cost nothing."""

import datetime

from dcs.mapping import LatLng
from dcs.planes import A_10C_2, AV8BNA, F_15ESE, F_16C_50, FA_18C_hornet

from game.dcs.aircraftproperties import PropertyDateGate, night_vision_overrides
from game.weather.daylight import in_darkness

DATE = datetime.date(2020, 6, 1)


def _overrides(unit_type: type, props: dict[str, object]) -> dict[str, object]:
    return dict(
        night_vision_overrides(
            unit_type.properties, props, PropertyDateGate(), DATE  # type: ignore[arg-type, attr-defined]
        )
    )


def test_a10c_hmcs_gains_the_goggles() -> None:
    assert _overrides(A_10C_2, {}) == {"HelmetMountedDevice": 2}


def test_a10c_without_a_helmet_stays_without() -> None:
    assert _overrides(A_10C_2, {"HelmetMountedDevice": 0}) == {}


def test_jhmcs_is_never_swapped_for_goggles() -> None:
    assert _overrides(F_16C_50, {}) == {}
    assert _overrides(FA_18C_hornet, {}) == {}


def test_a_goggle_mount_checkbox_is_ticked() -> None:
    assert _overrides(AV8BNA, {}) == {"MountNVG": True}
    assert _overrides(F_15ESE, {}) == {"MountNVG": True}


def test_a_checkbox_already_set_for_the_jet_is_kept() -> None:
    assert _overrides(AV8BNA, {"MountNVG": False}) == {}


def test_a_gated_combined_sight_is_not_fitted_early() -> None:
    gate = PropertyDateGate.from_data({"HelmetMountedDevice": {"HMCS + NVG": 2030}})
    assert dict(night_vision_overrides(A_10C_2.properties, {}, gate, DATE)) == {}


# Nellis, roughly: sunrise near 05:30 and sunset near 20:00 local in June.
NEVADA = LatLng(36.2, -115.0)
PDT = datetime.timezone(datetime.timedelta(hours=-7))


def _local(hour: int, minute: int = 0, day: int = 1) -> datetime.datetime:
    return datetime.datetime(2020, 6, day, hour, minute)


def test_a_midday_flight_is_in_daylight() -> None:
    assert not in_darkness(NEVADA, PDT, _local(11), _local(13))


def test_a_flight_landing_after_sunset_is_in_darkness() -> None:
    assert in_darkness(NEVADA, PDT, _local(18), _local(21))


def test_a_dawn_takeoff_before_sunrise_is_in_darkness() -> None:
    assert in_darkness(NEVADA, PDT, _local(4), _local(7))


def test_polar_night_is_dark_and_polar_day_is_not() -> None:
    kola = LatLng(69.0, 33.0)
    msk = datetime.timezone(datetime.timedelta(hours=3))
    winter = datetime.datetime(2020, 12, 21, 12)
    summer = datetime.datetime(2020, 6, 21, 12)
    assert in_darkness(kola, msk, winter, winter + datetime.timedelta(hours=1))
    assert not in_darkness(kola, msk, summer, summer + datetime.timedelta(hours=1))
