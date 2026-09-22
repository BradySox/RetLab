// §102: a point is saved as the kind picked, an orbit carries its racetrack, and a
// drawing needs two corners for a line and three for an area.
import DrawPanel from "./DrawPanel";
import SavePoint from "./SavePoint";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { LatLng } from "leaflet";

const AT = new LatLng(36.5886, -115.6736);

const HORNET = {
  id: "7",
  callsign: "STRIKE",
  aircraft: "F/A-18C",
  departure: "Nellis",
  kinds: ["waypoint", "ip", "target", "hold", "orbit"],
  room: { waypoint: 10, ip: 10, target: 10, hold: 10, orbit: 2 },
};

function answerWith(body: unknown) {
  const mock = jest.fn().mockResolvedValue({ ok: true, json: async () => body });
  global.fetch = mock as unknown as typeof fetch;
  return mock;
}

afterEach(() => {
  jest.resetAllMocks();
});

it("saves the kind that was picked", async () => {
  const mock = answerWith([HORNET]);
  render(<SavePoint at={AT} name="BRIDGE" />);

  const kind = await screen.findByDisplayValue("Waypoint");
  fireEvent.change(kind, { target: { value: "target" } });
  fireEvent.click(screen.getByText("Save as target"));

  await waitFor(() => expect(mock).toHaveBeenCalledTimes(2));
  const body = JSON.parse(mock.mock.calls[1][1].body);
  expect(body.kind).toBe("target");
});

it("asks an orbit for its heading and length", async () => {
  const mock = answerWith([HORNET]);
  render(<SavePoint at={AT} name="CAP" />);

  fireEvent.change(await screen.findByDisplayValue("Waypoint"), {
    target: { value: "orbit" },
  });
  fireEvent.change(screen.getByDisplayValue("90"), { target: { value: "270" } });
  fireEvent.click(screen.getByText("Save as orbit"));

  await waitFor(() => expect(mock).toHaveBeenCalledTimes(2));
  const body = JSON.parse(mock.mock.calls[1][1].body);
  expect(body.heading_deg).toBe(270);
  expect(body.length_nm).toBe(20);
});

it("offers drawing only where the picker handles it", async () => {
  answerWith([HORNET]);
  const onDraw = jest.fn();
  render(<SavePoint at={AT} name="X" onDraw={onDraw} />);

  fireEvent.click(await screen.findByText("Draw from here"));
  expect(onDraw).toHaveBeenCalled();
});

it("needs two corners for a line and three for an area", async () => {
  const mock = answerWith([HORNET]);
  const two = [AT, new LatLng(36.6, -115.7)];
  render(<DrawPanel points={two} undo={() => {}} close={() => {}} />);

  await screen.findByText(/STRIKE/);
  expect(screen.getByText("Save area")).toBeDisabled();
  fireEvent.click(screen.getByText("Save line"));

  await waitFor(() => expect(mock).toHaveBeenCalledTimes(2));
  expect(mock.mock.calls[1][0]).toMatch(/saved-points\/7\/drawings$/);
  const body = JSON.parse(mock.mock.calls[1][1].body);
  expect(body.closed).toBe(false);
  expect(body.points).toHaveLength(2);
});
