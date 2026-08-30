from types import SimpleNamespace
from typing import Any, cast

from dcs.mapping import Point
from dcs.terrain import Caucasus

from game.data.groups import GroupTask
from game.missiongenerator.motorpoolpopulator import MotorpoolPopulator
from game.theater.controlpoint import ControlPointType
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import MotorpoolGroundObject
from game.utils import Heading


def _land_cp(
    name: str, x: float, y: float, cptype: ControlPointType
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        cptype=cptype,
        position=Point(x, y, Caucasus()),
        connected_objectives=[],
        ground_objects=[],
    )


def _game(cps: list[Any]) -> Any:
    return SimpleNamespace(
        theater=SimpleNamespace(controlpoints=cps),
        settings=SimpleNamespace(motorpool_enabled=False, motorpool_spawn_cap=0),
    )


def _motorpool_owned_by(owner: Any, x: float, y: float) -> MotorpoolGroundObject:
    loc = PresetLocation("G", Point(x, y, Caucasus()), Heading.from_degrees(0.0))
    tgo = MotorpoolGroundObject("Motorpool 0", loc, owner, GroupTask.MOTORPOOL)
    owner.connected_objectives.append(tgo)
    return tgo


def _rehome(cps: list[Any]) -> None:
    MotorpoolPopulator(cast(Any, _game(cps)))._rehome_motorpools()


def test_rehome_moves_motorpool_to_nearest_farp() -> None:
    base = _land_cp("Countryside AB", 5000.0, 0.0, ControlPointType.AIRBASE)
    farp = _land_cp("Frontline FARP", 0.0, 0.0, ControlPointType.FARP)
    tgo = _motorpool_owned_by(base, 0.0, 0.0)

    _rehome([base, farp])

    assert tgo.control_point is farp
    assert base.connected_objectives == []
    assert farp.connected_objectives == [tgo]


def test_rehome_leaves_motorpool_on_nearest_base() -> None:
    base = _land_cp("Base", 0.0, 0.0, ControlPointType.AIRBASE)
    farp = _land_cp("Far FARP", 5000.0, 0.0, ControlPointType.FARP)
    tgo = _motorpool_owned_by(base, 0.0, 0.0)

    _rehome([base, farp])

    assert tgo.control_point is base
    assert base.connected_objectives == [tgo]
    assert farp.connected_objectives == []


def test_rehome_neutral_fob_claims_adjacent_motorpool() -> None:
    base = _land_cp("Enemy AB", -300000.0, 0.0, ControlPointType.AIRBASE)
    neutral_farp = _land_cp("Neutral FARP", 0.0, 0.0, ControlPointType.FARP)
    tgo = _motorpool_owned_by(base, 0.0, 0.0)

    _rehome([base, neutral_farp])

    # The neutral FOB wins; the motorpool follows its capture state (neutral).
    assert tgo.control_point is neutral_farp


def test_rehome_excludes_naval_control_points() -> None:
    base = _land_cp("AB", 5000.0, 0.0, ControlPointType.AIRBASE)
    carrier = _land_cp("CVN", 0.0, 0.0, ControlPointType.AIRCRAFT_CARRIER_GROUP)
    tgo = _motorpool_owned_by(base, 0.0, 0.0)

    _rehome([base, carrier])

    # Carrier is excluded, so the motorpool stays with the airbase.
    assert tgo.control_point is base


def test_populate_does_not_rehome_existing_motorpools() -> None:
    owner = _land_cp("Owner", 5000.0, 0.0, ControlPointType.AIRBASE)
    nearest = _land_cp("Nearest", 0.0, 0.0, ControlPointType.FARP)
    tgo = _motorpool_owned_by(owner, 0.0, 0.0)

    populator = MotorpoolPopulator(cast(Any, _game([owner, nearest])))
    populator.populate()

    assert tgo.control_point is owner
    assert owner.connected_objectives == [tgo]
    assert nearest.connected_objectives == []
