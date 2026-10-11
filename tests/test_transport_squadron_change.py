"""Changing a transport flight's squadron keeps its cargo moving.

The replacement flight took the old flight's cargo, then removing the old flight
cleared the cargo's transport, and the next flight-plan build raised
``TransferOrder.next_stop called with no transport assigned``. Ported from
rmac7664/dcs-retribution, on the fork's lift-slot capacity.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from game.ato.package import Package
from game.data.units import UnitClass
from game.theater.player import Player
from game.transfers import Airlift, PendingTransfers, TransferOrder, reassign_cargo


@dataclass(frozen=True)
class FakeGroundUnit:
    unit_class: UnitClass


def _aircraft(slots: int) -> Any:
    return SimpleNamespace(
        airlift_capacity=slots, dcs_unit_type=SimpleNamespace(helicopter=False)
    )


def _transport(cargo: TransferOrder) -> Any:
    # Read through Any: mypy narrows the attribute after each assignment.
    return cargo.transport


INFANTRY: Any = FakeGroundUnit(UnitClass.INFANTRY)
ORIGIN: Any = SimpleNamespace(name="Origin")
MIDDLE: Any = SimpleNamespace(name="Middle")
DESTINATION: Any = SimpleNamespace(name="Destination")


def _flight(flight_id: int, cargo: TransferOrder, slots: int, count: int = 1) -> Any:
    return SimpleNamespace(
        id=flight_id,
        cargo=cargo,
        count=count,
        unit_type=_aircraft(slots),
        return_pilots_and_aircraft=lambda: None,
    )


def _game(pending: list[TransferOrder]) -> Any:
    transfers = PendingTransfers.__new__(PendingTransfers)
    transfers.pending_transfers = pending
    return SimpleNamespace(
        coalition_for=lambda _player: SimpleNamespace(transfers=transfers)
    )


def _replace(old: Any, new: Any, game: Any) -> int:
    """What QFlightSlotEditor._change_squadron does to the cargo."""
    left_behind = reassign_cargo(game, new, DESTINATION)
    package: Any = SimpleNamespace(
        flights=[old, new], _db=SimpleNamespace(remove=lambda _id: None), waypoints=1
    )
    Package.remove_flight(package, old)
    return left_behind


def test_the_replacement_flight_keeps_a_transport() -> None:
    cargo = TransferOrder(ORIGIN, DESTINATION, {INFANTRY: 2}, player=Player.BLUE)
    old = _flight(1, cargo, slots=4)
    cargo.transport = Airlift(cargo, old, DESTINATION)
    new = _flight(2, cargo, slots=4)

    assert _replace(old, new, _game([cargo])) == 0

    assert isinstance(_transport(cargo), Airlift)
    assert _transport(cargo).flight is new
    assert cargo.next_stop is DESTINATION


def test_cancelling_a_transport_flight_still_frees_its_cargo() -> None:
    cargo = TransferOrder(ORIGIN, DESTINATION, {INFANTRY: 2}, player=Player.BLUE)
    flight = _flight(1, cargo, slots=4)
    cargo.transport = Airlift(cargo, flight, DESTINATION)
    package: Any = SimpleNamespace(
        flights=[flight], _db=SimpleNamespace(remove=lambda _id: None), waypoints=1
    )

    Package.remove_flight(package, flight)

    assert _transport(cargo) is None


def test_what_a_smaller_aircraft_cannot_lift_waits_for_the_next_transport() -> None:
    cargo = TransferOrder(ORIGIN, DESTINATION, {INFANTRY: 3}, player=Player.BLUE)
    old = _flight(1, cargo, slots=4)
    cargo.transport = Airlift(cargo, old, DESTINATION)
    new = _flight(2, cargo, slots=2)
    pending = [cargo]

    assert _replace(old, new, _game(pending)) == 1

    assert new.cargo is not cargo
    assert new.cargo.size == 2
    assert new.cargo.transport.flight is new
    assert cargo.size == 1
    assert _transport(cargo) is None
    assert pending == [cargo, new.cargo]


def test_a_split_part_stays_where_the_cargo_is() -> None:
    transfer = TransferOrder(ORIGIN, DESTINATION, {INFANTRY: 4}, player=Player.BLUE)
    transfer.position = MIDDLE
    transfers = PendingTransfers.__new__(PendingTransfers)
    transfers.pending_transfers = [transfer]

    part = transfers.split_transfer(transfer, 1)

    assert part.position is MIDDLE
    assert part.size == 1 and transfer.size == 3
