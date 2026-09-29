from types import SimpleNamespace
from typing import Any

from dcs.mapping import Point

from game.ato.flightplans.planningerror import PlanningError
from game.theater.controlpoint import OffMapSpawn, Player
from game.theater.instantnavalmove import (
    destination_is_open_sea,
    move_control_point_now,
)
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import CarrierGroundObject
from game.utils import Heading


class _Events:
    def __init__(self) -> None:
        self.flights: list[Any] = []
        self.cps: list[Any] = []
        self.tgos: list[Any] = []

    def update_flight(self, flight: Any) -> None:
        self.flights.append(flight)

    def update_control_point(self, cp: Any) -> None:
        self.cps.append(cp)

    def update_tgo(self, tgo: Any) -> None:
        self.tgos.append(tgo)


class _Flight:
    def __init__(self, departure: Any, fail: bool = False) -> None:
        self.departure = departure
        self.arrival = departure
        self.divert = None
        self.flight_plan = None
        self.replanned = False
        self.fail = fail

    def recreate_flight_plan(self) -> None:
        if self.fail:
            raise PlanningError("no plan")
        self.replanned = True


def _carrier_cp() -> tuple[OffMapSpawn, CarrierGroundObject, Any]:
    cp = OffMapSpawn(
        name="boat",
        position=Point(0, 0, None),  # type: ignore[arg-type]
        theater=None,  # type: ignore[arg-type]
        starts_blue=Player.BLUE,
    )
    location = PresetLocation(
        name="loc", position=Point(0, 0, None), heading=Heading(0)  # type: ignore[arg-type]
    )
    carrier = CarrierGroundObject(name="CVN-71", location=location, control_point=cp)
    unit: Any = SimpleNamespace(position=Point(0, 0, None))  # type: ignore[arg-type]
    carrier.groups.append(SimpleNamespace(units=[unit]))  # type: ignore[arg-type]
    cp.connected_objectives.append(carrier)
    return cp, carrier, unit


def _queue(cp: OffMapSpawn, x: float, y: float) -> None:
    cp.target_position = Point(x, y, None)  # type: ignore[arg-type]


def _game(packages: list[Any], sea: bool = True) -> Any:
    threat_zones: list[Any] = []
    return SimpleNamespace(
        settings=SimpleNamespace(enable_instant_naval_move_cheat=True),
        theater=SimpleNamespace(
            landmap=SimpleNamespace(land_inbetween=lambda a, b: True),
            is_in_sea=lambda p: sea,
        ),
        coalitions=[SimpleNamespace(ato=SimpleNamespace(packages=packages))],
        compute_threat_zones=lambda events: threat_zones.append(events),
        threat_zones=threat_zones,
    )


def test_carrier_and_its_units_arrive_now() -> None:
    cp, carrier, unit = _carrier_cp()
    _queue(cp, 90000, 5000)
    game = _game([])
    events = _Events()

    move_control_point_now(game, cp, events)  # type: ignore[arg-type]

    assert cp.target_position is None
    assert (cp.position.x, cp.position.y) == (90000, 5000)
    assert (carrier.position.x, carrier.position.y) == (90000, 5000)
    assert (unit.position.x, unit.position.y) == (90000, 5000)
    assert events.cps == [cp] and events.tgos == [carrier]
    assert len(game.threat_zones) == 1


def test_only_flights_from_or_against_the_boat_are_replanned() -> None:
    cp, carrier, _ = _carrier_cp()
    _queue(cp, 1000, 0)
    from_boat = _Flight(departure=cp)
    elsewhere = _Flight(departure=object())
    against_boat = _Flight(departure=object())
    unplannable = _Flight(departure=cp, fail=True)
    packages = [
        SimpleNamespace(target=object(), flights=[from_boat, elsewhere, unplannable]),
        SimpleNamespace(target=carrier, flights=[against_boat]),
    ]
    events = _Events()

    move_control_point_now(_game(packages), cp, events)  # type: ignore[arg-type]

    assert from_boat.replanned and against_boat.replanned
    assert not elsewhere.replanned
    assert events.flights == [from_boat, against_boat]


def test_cheat_needs_only_a_sea_destination() -> None:
    origin = Point(0, 0, None)  # type: ignore[arg-type]
    dest = Point(1, 1, None)  # type: ignore[arg-type]
    assert destination_is_open_sea(_game([]), origin, dest)
    assert not destination_is_open_sea(_game([], sea=False), origin, dest)
