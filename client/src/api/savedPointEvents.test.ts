// §102: the event stream tells the saved-points layer when to re-read.
//
// Ported from juanjux/dcs-escalation (LGPL-3.0).
import { CHANGED_EVENT } from "../components/coordinatepicker/receivers";
import { handleStreamedEvents } from "./eventstream";

jest.mock("./gamestate", () => ({ __esModule: true, default: jest.fn() }));

const emptyEvents = {
  updated_flight_positions: {},
  new_combats: [],
  updated_combats: [],
  ended_combats: [],
  navmesh_updates: [],
  updated_unculled_zones: [],
  threat_zones_updated: [],
  new_flights: [],
  updated_flights: [],
  deleted_flights: [],
  selected_flight: null,
  deselected_flight: false,
  updated_front_lines: [],
  deleted_front_lines: [],
  updated_tgos: [],
  deleted_tgos: [],
  updated_control_points: [],
  updated_iads: [],
  deleted_iads: [],
  updated_supply_routes: [],
  reset_on_map_center: null,
  game_unloaded: false,
  new_turn: false,
};

it.each([
  { saved_points_updated: true },
  { deleted_flights: ["flight-1"] },
  { new_turn: true },
  { game_unloaded: true },
])("tells the layer about a change that matters to it: %j", (changes) => {
  const listener = jest.fn();
  window.addEventListener(CHANGED_EVENT, listener);
  handleStreamedEvents(jest.fn(), { ...emptyEvents, ...changes });
  expect(listener).toHaveBeenCalledTimes(1);
  expect(listener.mock.calls[0][0].detail).toEqual({
    unloaded: "game_unloaded" in changes,
    reset: "new_turn" in changes,
  });
  window.removeEventListener(CHANGED_EVENT, listener);
});

it("says nothing for a simulation update that touches no flight", () => {
  const listener = jest.fn();
  window.addEventListener(CHANGED_EVENT, listener);
  handleStreamedEvents(jest.fn(), emptyEvents);
  expect(listener).not.toHaveBeenCalled();
  window.removeEventListener(CHANGED_EVENT, listener);
});
