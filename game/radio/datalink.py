"""DATALINK handling."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterator, Mapping, Optional, Set

from game.dcs.aircrafttype import AircraftType

VOICE_CALLSIGN_LABEL = "VoiceCallsignLabel"
VOICE_CALLSIGN_NUMBER = "VoiceCallsignNumber"
OWNSHIP_CALLSIGN = "OwnshipCallSign"


class DataLinkKey(Enum):
    LINK16 = "STN_L16"
    SADL = "SADL_TN"
    IDM = "TN_IDM_LB"
    Unknown = "Unsupported type"

    @staticmethod
    def from_aircraft_type(ac_type: AircraftType) -> DataLinkKey:
        dcs_type = ac_type.dcs_unit_type
        if DataLinkKey.LINK16.value in dcs_type.properties:
            return DataLinkKey.LINK16
        elif DataLinkKey.SADL.value in dcs_type.properties:
            return DataLinkKey.SADL
        elif DataLinkKey.IDM.value in dcs_type.properties:
            return DataLinkKey.IDM
        return DataLinkKey.Unknown

    def range(self) -> Iterator["DataLinkIdentifier"]:
        match self.value:
            case DataLinkKey.LINK16.value:
                return (
                    DataLinkIdentifier(str(f"{x:05o}"), self) for x in range(1, 0o77777)
                )
            case DataLinkKey.SADL.value:
                return (
                    DataLinkIdentifier(str(f"{x:04o}"), self) for x in range(1, 0o7777)
                )
            case DataLinkKey.IDM.value:
                return (DataLinkIdentifier(x, self) for x in self._idm_ids())

        raise RuntimeError(f"No range for datalink-type: {self.value}")

    def normalize(self, raw: str) -> str:
        """A typed identifier in the allocator's own form (zero-padded octal)."""
        raw = raw.strip().upper()
        match self.value:
            case DataLinkKey.LINK16.value:
                return raw.zfill(5)
            case DataLinkKey.SADL.value:
                return raw.zfill(4)
        return raw

    def valid_identifiers(self) -> Iterator["DataLinkIdentifier"]:
        for x in self.range():
            yield x

    @staticmethod
    def _idm_ids() -> Iterator[str]:  # TODO: there must be a better place for this...
        second_range = [str(x) for x in range(1, 10)]
        for single in second_range:
            yield f"{single}"
        for first in range(1, 4):
            second_range = [str(x) for x in range(1, 10)]
            if first < 3:
                second_range.extend([str(chr(x)) for x in range(65, 91)])
            else:
                second_range.extend([str(chr(x)) for x in range(65, 74)])
            for second in second_range:
                yield f"{first}{second}"


@dataclass
class DataLinkIdentifier:
    id: str
    type: DataLinkKey

    def __hash__(self) -> int:
        return f"{self.id} - {self.type.value}".__hash__()


#: Every property the DATALINK group of the payload editor can hold. They name one
#: jet, so nothing may copy them from one aircraft to another.
DATALINK_PROPERTY_IDS = frozenset(
    {VOICE_CALLSIGN_LABEL, VOICE_CALLSIGN_NUMBER, OWNSHIP_CALLSIGN}
    | {key.value for key in DataLinkKey if key is not DataLinkKey.Unknown}
)


def typed_identifier(
    ac_type: AircraftType, props: Mapping[str, object]
) -> Optional[DataLinkIdentifier]:
    """The identifier the player typed for one aircraft, or None when left blank."""
    key = DataLinkKey.from_aircraft_type(ac_type)
    raw = props.get(key.value)
    if not isinstance(raw, str) or not raw.strip():
        return None
    return DataLinkIdentifier(key.normalize(raw), key)


class OutOfIdentifiersError(RuntimeError):
    """Raised when all channels in this band have been allocated."""

    def __init__(self, type: DataLinkKey) -> None:
        super().__init__(
            f"No available identifiers left for datalink-type {type.value}"
        )


class DataLinkRegistry:
    """Manages allocation of DATALINK identifiers."""

    def __init__(self) -> None:
        self.allocated_identifiers: Set[DataLinkIdentifier] = set()
        self.allocators: Dict[DataLinkKey, Iterator[DataLinkIdentifier]] = {}

        for type in DataLinkKey:
            self.allocators[type] = type.valid_identifiers()

    def alloc_for_aircraft(self, ac_type: AircraftType) -> DataLinkIdentifier:
        datalink_type = DataLinkKey.from_aircraft_type(ac_type)
        allocator = self.allocators[datalink_type]
        try:
            while (identifier := next(allocator)) in self.allocated_identifiers:
                pass
            self.mark_unavailable(identifier)
            return identifier
        except StopIteration:
            raise OutOfIdentifiersError(datalink_type)

    def mark_unavailable(self, identifier: DataLinkIdentifier) -> None:
        self.allocated_identifiers.add(identifier)
