"""A datalink identifier typed in the payload editor is kept, and kept unique.

Left blank, the generator allocates the STN and derives the voice callsign. A typed
STN used to skip the whole fill, so the jet got no voice callsign and the allocator
could hand the same STN to another aircraft.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dcs.helicopters import AH_64D_BLK_II
from dcs.planes import A_10C_2, FA_18C_hornet

from game.missiongenerator.aircraft.aircraftgenerator import AircraftGenerator
from game.missiongenerator.aircraft.flightgroupconfigurator import (
    FlightGroupConfigurator,
)
from game.radio.datalink import (
    DATALINK_PROPERTY_IDS,
    DataLinkKey,
    DataLinkRegistry,
    typed_identifier,
)


def _ac(dcs_type: Any) -> Any:
    return SimpleNamespace(dcs_unit_type=dcs_type)


def _configurator(registry: DataLinkRegistry, dcs_type: Any) -> Any:
    return SimpleNamespace(
        datalink_registry=registry,
        flight=SimpleNamespace(unit_type=_ac(dcs_type)),
        set_datalink_props=FlightGroupConfigurator.set_datalink_props,
    )


def _generator(registry: DataLinkRegistry) -> Any:
    return SimpleNamespace(datalink_registry=registry)


def _flight(dcs_type: Any, *member_props: dict[str, Any]) -> Any:
    members = [SimpleNamespace(properties=dict(p)) for p in member_props]
    return SimpleNamespace(unit_type=_ac(dcs_type), iter_members=lambda: iter(members))


def test_property_ids_cover_every_datalink_box() -> None:
    assert DATALINK_PROPERTY_IDS == {
        "STN_L16",
        "SADL_TN",
        "TN_IDM_LB",
        "VoiceCallsignLabel",
        "VoiceCallsignNumber",
        "OwnshipCallSign",
    }


def test_blank_box_is_not_a_typed_identifier() -> None:
    assert typed_identifier(_ac(FA_18C_hornet), {}) is None
    assert typed_identifier(_ac(FA_18C_hornet), {"STN_L16": ""}) is None
    # Another link's key on this airframe is not its identifier.
    assert typed_identifier(_ac(FA_18C_hornet), {"SADL_TN": "0012"}) is None


def test_typed_identifier_is_padded_like_an_allocated_one() -> None:
    hornet = typed_identifier(_ac(FA_18C_hornet), {"STN_L16": "5"})
    assert hornet is not None and (hornet.id, hornet.type) == (
        "00005",
        DataLinkKey.LINK16,
    )
    hog = typed_identifier(_ac(A_10C_2), {"SADL_TN": "12"})
    assert hog is not None and (hog.id, hog.type) == ("0012", DataLinkKey.SADL)
    apache = typed_identifier(_ac(AH_64D_BLK_II), {"TN_IDM_LB": "2a"})
    assert apache is not None and (apache.id, apache.type) == ("2A", DataLinkKey.IDM)


def test_typed_stn_is_kept_and_the_voice_callsign_still_filled() -> None:
    props: dict[str, Any] = {"STN_L16": "00123"}
    FlightGroupConfigurator.set_datalink(
        _configurator(DataLinkRegistry(), FA_18C_hornet), props, "Squid41"
    )
    assert props == {
        "STN_L16": "00123",
        "VoiceCallsignLabel": "SD",
        "VoiceCallsignNumber": "41",
    }


def test_typed_voice_callsign_is_kept_around_an_allocated_stn() -> None:
    props: dict[str, Any] = {"VoiceCallsignLabel": "BB"}
    FlightGroupConfigurator.set_datalink(
        _configurator(DataLinkRegistry(), FA_18C_hornet), props, "Squid41"
    )
    assert props == {
        "STN_L16": "00001",
        "VoiceCallsignLabel": "BB",
        "VoiceCallsignNumber": "41",
    }


def test_allocator_skips_an_stn_a_player_typed() -> None:
    registry = DataLinkRegistry()
    AircraftGenerator._reserve_typed_datalink_identifiers(
        _generator(registry),
        _flight(FA_18C_hornet, {"STN_L16": "1"}, {}, {"STN_L16": "00003"}),
    )
    allocated = [registry.alloc_for_aircraft(_ac(FA_18C_hornet)).id for _ in range(2)]
    assert allocated == ["00002", "00004"]


def test_typed_stn_does_not_reserve_another_links_number() -> None:
    registry = DataLinkRegistry()
    AircraftGenerator._reserve_typed_datalink_identifiers(
        _generator(registry), _flight(FA_18C_hornet, {"STN_L16": "00001"})
    )
    assert registry.alloc_for_aircraft(_ac(A_10C_2)).id == "0001"
