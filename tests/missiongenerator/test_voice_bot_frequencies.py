"""Voice bot frequencies (§116-§119): who stays off them, and what survives both sides."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.ato.flighttype import FlightType
from game.missiongenerator.aircraft.aircraftgenerator import AircraftGenerator
from game.missiongenerator.aircraft.flightgroupconfigurator import (
    FlightGroupConfigurator,
)
from game.missiongenerator.missiondata import MissionData
from game.missiongenerator.missiongenerator import (
    MissionGenerator,
    dcs_default_group_frequencies,
    reserve_ato_frequencies,
)
from game.radio.radios import MHz, RadioRegistry
from game.retlab.package_control import player_packages


class _Unlinkable:
    """A flight the datalink pass must not touch."""

    @property
    def aircraft_type(self) -> Any:
        raise AssertionError("the other side's package was linked again")


def test_the_red_pass_keeps_blue_packages_for_package_control() -> None:
    blue: Any = SimpleNamespace(
        friendly=SimpleNamespace(is_blue=True),
        client_units=[object()],
        flight_type=None,
    )
    generator: Any = AircraftGenerator.__new__(AircraftGenerator)
    generator.mission_data = MissionData()
    generator.mission_data.packages[1] = [blue]
    generator._reserve_frequencies_and_tacan = lambda ato: None
    red_ato: Any = SimpleNamespace(packages=[])
    generator.generate_flights(red_ato, {})
    assert player_packages(generator.mission_data) == [[blue]]


def test_each_pass_links_only_its_own_packages() -> None:
    generator: Any = AircraftGenerator.__new__(AircraftGenerator)
    generator.mission_data = MissionData()
    generator.mission_data.packages[1] = [_Unlinkable()]  # type: ignore[list-item]
    generator._link_datalink_on_package_level_and_awacs({2})


def test_voice_bots_never_take_a_dcs_default_group_frequency() -> None:
    defaults = dcs_default_group_frequencies()
    assert {MHz(124), MHz(127, 500), MHz(251), MHz(305)} <= defaults
    registry = RadioRegistry()
    with registry.holding(defaults):
        picked = [registry.alloc_uhf() for _ in range(100)]
    assert not set(picked) & defaults
    # Held, not reserved: a carrier's curated 305.0 can still have it.
    assert not registry.allocated_channels & defaults


def test_hand_set_ato_frequencies_are_reserved_first_on_both_sides() -> None:
    def side(package_mhz: int, flight_mhz: int) -> Any:
        flight = SimpleNamespace(frequency=MHz(flight_mhz))
        package = SimpleNamespace(frequency=MHz(package_mhz), flights=[flight])
        return SimpleNamespace(ato=SimpleNamespace(packages=[package]))

    game: Any = SimpleNamespace(blue=side(260, 261), red=side(262, 260))
    registry = RadioRegistry()
    reserve_ato_frequencies(game, registry)
    assert {MHz(260), MHz(261), MHz(262)} <= registry.allocated_channels


def _group(mhz: float, human: bool = False, name: str = "group") -> Any:
    unit = SimpleNamespace(is_human=lambda: human)
    return SimpleNamespace(name=name, frequency=mhz, units=[unit])


def test_ai_groups_move_off_every_voice_bot_frequency() -> None:
    data = MissionData()
    data.skyeye_frequency = MHz(251)
    data.strike_frequency = MHz(264)
    data.vacuum_frequency = MHz(270)
    data.atc_frequencies = {"Kobuleti": (MHz(280), MHz(281))}
    on_bots = [_group(f) for f in (251.0, 264.0, 270.0, 280.0, 281.0)]
    player, other = _group(264.0, human=True), _group(124.0)
    country = SimpleNamespace(plane_group=[*on_bots, player], helicopter_group=[other])
    generator: Any = MissionGenerator.__new__(MissionGenerator)
    generator.mission_data = data
    generator.radio_registry = RadioRegistry()
    for f in data.voice_bot_frequencies():
        generator.radio_registry.reserve(f)
    generator.mission = SimpleNamespace(
        coalition={"blue": SimpleNamespace(countries={"USA": country})}
    )
    generator._move_ai_off_voice_bots()
    bots = {f.mhz for f in data.voice_bot_frequencies()}
    assert all(g.frequency not in bots for g in on_bots)
    assert player.frequency == 264.0
    assert other.frequency == 124.0


def test_strike_is_a_package_frequency_only_in_the_mission() -> None:
    data = MissionData()
    package: Any = SimpleNamespace(frequency=MHz(262))
    assert data.package_frequency(package) == MHz(262)
    data.strike_frequency = MHz(264)
    data.strike_packages.add(id(package))
    assert data.package_frequency(package) == MHz(264)
    assert package.frequency == MHz(262)


def _setup_radios(data: MissionData, package: Any, client_count: int) -> Any:
    group = SimpleNamespace(name="Hornet 1", frequency=None)
    group.set_frequency = lambda mhz: setattr(group, "frequency", mhz)
    configurator: Any = object.__new__(FlightGroupConfigurator)
    configurator.flight = SimpleNamespace(
        frequency=None,
        package=package,
        flight_type=FlightType.STRIKE,
        client_count=client_count,
        squadron=SimpleNamespace(radio_presets={"intra_flight": [MHz(301)]}),
    )
    configurator.group = group
    configurator.mission_data = data
    configurator.radio_registry = RadioRegistry()
    configurator.setup_radios()
    return group


def test_ai_in_a_player_package_fly_on_strike() -> None:
    data = MissionData()
    data.strike_frequency = MHz(264)
    package: Any = SimpleNamespace(frequency=MHz(262))
    data.strike_packages.add(id(package))
    assert _setup_radios(data, package, client_count=0).frequency == 264.0
    assert data.strike_groups == {"Hornet 1"}
    # The package keeps its own frequency in the save.
    assert package.frequency == MHz(262)


def test_players_and_other_packages_keep_their_frequencies() -> None:
    data = MissionData()
    data.strike_frequency = MHz(264)
    package: Any = SimpleNamespace(frequency=MHz(262))
    other: Any = SimpleNamespace(frequency=MHz(263))
    data.strike_packages.add(id(package))
    assert _setup_radios(data, package, client_count=1).frequency == 301.0
    assert _setup_radios(data, other, client_count=0).frequency == 263.0
    assert not data.strike_groups


def test_the_sweep_leaves_package_ai_on_strike() -> None:
    data = MissionData()
    data.strike_frequency = MHz(264)
    data.vacuum_frequency = MHz(270)
    data.strike_groups = {"Hornet 1"}
    package_ai = _group(264.0, name="Hornet 1")
    stray = _group(264.0, name="Tanker 1")
    on_vacuum = _group(270.0, name="Hornet 1")
    country = SimpleNamespace(
        plane_group=[package_ai, stray, on_vacuum], helicopter_group=[]
    )
    generator: Any = MissionGenerator.__new__(MissionGenerator)
    generator.mission_data = data
    generator.radio_registry = RadioRegistry()
    for f in data.voice_bot_frequencies():
        generator.radio_registry.reserve(f)
    generator.mission = SimpleNamespace(
        coalition={"blue": SimpleNamespace(countries={"USA": country})}
    )
    generator._move_ai_off_voice_bots()
    assert package_ai.frequency == 264.0
    assert stray.frequency not in (264.0, 270.0)
    assert on_vacuum.frequency not in (264.0, 270.0)


def test_each_side_escapes_to_its_own_frequency_off_the_dcs_defaults() -> None:
    data = MissionData()
    data.skyeye_frequency = MHz(251)
    sides = {
        side: [_group(251.0, name=f"{side} {n}") for n in range(2)]
        for side in ("blue", "red", "neutrals")
    }
    generator: Any = MissionGenerator.__new__(MissionGenerator)
    generator.mission_data = data
    generator.radio_registry = RadioRegistry()
    generator.radio_registry.reserve(MHz(251))
    generator.mission = SimpleNamespace(
        coalition={
            side: SimpleNamespace(
                countries={
                    side: SimpleNamespace(plane_group=groups, helicopter_group=[])
                }
            )
            for side, groups in sides.items()
        }
    )
    generator._move_ai_off_voice_bots()
    escapes = {side: {g.frequency for g in groups} for side, groups in sides.items()}
    assert all(len(e) == 1 for e in escapes.values())
    picked = {e.pop() for e in escapes.values()}
    assert len(picked) == 3
    defaults = {f.mhz for f in dcs_default_group_frequencies()}
    assert not picked & defaults
    # The defaults are only held for the sweep; a later allocation may use them.
    held = set(dcs_default_group_frequencies()) - {MHz(251)}
    assert not generator.radio_registry.allocated_channels & held
