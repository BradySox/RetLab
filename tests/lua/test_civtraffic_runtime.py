"""Headless runtime checks for the civtraffic plugin (civtraffic-config.lua).

The contract: each layer is held at its target. A flight that lands, reaches its
map-edge exit, never takes off or outlives its max age is removed, and a queued one is
switched on in its place, at most two a tick and never two from one field within three
minutes. No node is a clean no-op. Whether DCS flies the traffic well is in-game only.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/civtraffic/civtraffic-config.lua"
NEUTRAL = 0


def _flight(
    name: str,
    queued: bool = True,
    layer: str = "airway",
    exit_xz: tuple[int, int] | None = None,
    field: str | None = None,
    max_age: int = 14_400,
) -> dict[str, Any]:
    flight: dict[str, Any] = {
        "group": name,
        "layer": layer,
        "queued": "true" if queued else "",
        "maxAge": str(max_age),
    }
    if exit_xz is not None:
        flight["exitX"], flight["exitZ"] = str(exit_xz[0]), str(exit_xz[1])
    if field is not None:
        flight["field"] = field
    return flight


def _group(name: str, airborne: bool = False, x: int = 0, z: int = 0) -> dict[str, Any]:
    return {
        "name": name,
        "id": len(name) * 100 + sum(map(ord, name)),
        "side": NEUTRAL,
        "category": 0,
        "units": [
            {
                "name": name + " #1",
                "type": "Yak-40",
                "x": x,
                "z": z,
                "airborne": airborne,
            }
        ],
    }


def _load(
    flights: list[dict[str, Any]], targets: dict[str, str] | None = None
) -> DcsPluginHarness:
    h = DcsPluginHarness()
    for flight in flights:
        h.add_group(_group(flight["group"], airborne=flight["queued"] == ""))
    node = {"targets": targets or {"airway": "2", "hop": "0"}, "flights": flights}
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}, "civilTraffic": node})
    h.load_plugin_script(PLUGIN)
    return h


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.set_retribution_config()
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert h.records("activations") == []
    assert h.pending_scheduled() == 0


def test_the_queue_tops_each_layer_up_to_its_target() -> None:
    h = _load([_flight("Live 1", queued=False), _flight("Q 1"), _flight("Q 2")])
    h.advance_to(31)
    assert h.records("activations") == ["Q 1"]  # 1 live + 1 = target 2
    h.assert_no_lua_errors()


def test_at_most_two_switch_on_a_tick() -> None:
    flights = [_flight(f"Q {i}") for i in range(5)]
    h = _load(flights, targets={"airway": "5"})
    h.advance_to(31)
    assert len(h.records("activations")) == 2
    h.advance_to(61)
    assert len(h.records("activations")) == 4


def test_two_departures_from_one_field_are_spaced() -> None:
    flights = [_flight("Q 1", field="Batumi"), _flight("Q 2", field="Batumi")]
    h = _load(flights, targets={"airway": "2"})
    h.advance_to(31)
    assert h.records("activations") == ["Q 1"]
    h.advance_to(211)
    assert h.records("activations") == ["Q 1", "Q 2"]


def test_a_flight_that_leaves_the_map_is_replaced() -> None:
    flights = [
        _flight("Live 1", queued=False, exit_xz=(100_000, 0)),
        _flight("Q 1"),
    ]
    h = _load(flights, targets={"airway": "1"})
    h.advance_to(31)
    assert h.records("activations") == []
    h.update_unit("Live 1", {"x": 95_000, "z": 3_000})
    h.advance_to(61)
    assert h.records("destroys") == ["Live 1"]
    assert h.records("activations") == ["Q 1"]


def test_a_landed_flight_is_removed_after_it_rolls_out() -> None:
    h = _load([_flight("Live 1", queued=False), _flight("Q 1")], {"airway": "1"})
    h.advance_to(31)
    h.update_unit("Live 1", {"airborne": False})
    h.advance_to(61)
    assert h.records("destroys") == []  # still rolling out
    h.advance_to(151)
    assert h.records("destroys") == ["Live 1"]
    assert h.records("activations") == ["Q 1"]


def test_a_flight_that_never_takes_off_is_removed() -> None:
    h = _load([_flight("Q 1"), _flight("Q 2")], {"airway": "1"})
    h.advance_to(31)
    assert h.records("activations") == ["Q 1"]
    h.advance_to(31 + 900)
    assert h.records("destroys") == ["Q 1"]
    assert h.records("activations") == ["Q 1", "Q 2"]


def test_a_flight_past_its_max_age_is_removed() -> None:
    h = _load([_flight("Live 1", queued=False, max_age=600)], {"airway": "1"})
    h.advance_to(631)
    assert h.records("destroys") == ["Live 1"]


def test_a_shot_down_flight_frees_its_slot() -> None:
    h = _load([_flight("Live 1", queued=False), _flight("Q 1")], {"airway": "1"})
    h.update_unit("Live 1", {"exists": False})
    h.advance_to(31)
    assert h.records("activations") == ["Q 1"]
    assert h.records("destroys") == []


def test_layers_are_counted_apart() -> None:
    flights = [
        _flight("Airway live", queued=False),
        _flight("Hop Q", layer="hop"),
        _flight("Airway Q"),
    ]
    h = _load(flights, targets={"airway": "1", "hop": "1"})
    h.advance_to(31)
    assert h.records("activations") == ["Hop Q"]
