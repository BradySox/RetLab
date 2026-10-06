"""The StopOrbit backstop is per flight, not per package (upstream #964)."""

from dcs import Mission
from dcs.task import ControlledTask, OrbitAction

from game.missiongenerator.aircraft.waypoints._helper import create_stop_orbit_trigger


def _orbit() -> ControlledTask:
    return ControlledTask(OrbitAction(pattern=OrbitAction.OrbitPattern.RaceTrack))


def _flag_of(orbit: ControlledTask) -> str:
    return str(orbit.params["stopCondition"]["userFlag"])


def test_each_group_gets_its_own_stop_flag_and_trigger() -> None:
    # A flag fires once: one package-wide flag ended the AWACS at the BARCAP's time.
    mission = Mission()
    awacs, barcap = _orbit(), _orbit()
    create_stop_orbit_trigger(awacs, 21, mission, 15780)
    create_stop_orbit_trigger(barcap, 20, mission, 8520)

    assert _flag_of(awacs) != _flag_of(barcap)
    assert len(mission.triggerrules.triggers) == 2


def test_the_same_orbit_is_only_given_one_trigger() -> None:
    mission = Mission()
    create_stop_orbit_trigger(_orbit(), 20, mission, 8520)
    create_stop_orbit_trigger(_orbit(), 20, mission, 8520)
    assert len(mission.triggerrules.triggers) == 1


def test_two_orbits_of_one_group_keep_their_own_end_times() -> None:
    mission = Mission()
    hold, loiter = _orbit(), _orbit()
    create_stop_orbit_trigger(hold, 20, mission, 1200)
    create_stop_orbit_trigger(loiter, 20, mission, 4800)
    assert _flag_of(hold) != _flag_of(loiter)
    assert len(mission.triggerrules.triggers) == 2


def test_the_flag_is_stable_across_generations() -> None:
    # The old flag was a Python id(), an object address that changes per run.
    first, second = _orbit(), _orbit()
    create_stop_orbit_trigger(first, 20, Mission(), 8520)
    create_stop_orbit_trigger(second, 20, Mission(), 8520)
    assert _flag_of(first) == _flag_of(second)


def test_the_trigger_sets_the_flag_the_orbit_waits_on() -> None:
    mission = Mission()
    orbit = _orbit()
    create_stop_orbit_trigger(orbit, 20, mission, 8520)
    [trigger] = mission.triggerrules.triggers
    script = trigger.actions[0].dict()["text"]
    assert script == f'trigger.action.setUserFlag("{_flag_of(orbit)}", true)'
