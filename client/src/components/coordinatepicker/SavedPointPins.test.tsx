// §102: each saved point is one pin on the map, renamed, deleted and moved by its
// id, and redrawn whenever the server or the map says something changed.
//
// Ported from juanjux/dcs-escalation (LGPL-3.0).
import SavedPointPin, { pinIcon } from "./SavedPointPin";
import SavedPointsLayer from "./SavedPointsLayer";
import { CHANGED_EVENT, Receiver, SavedPointJs } from "./receivers";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";

const mockSetLatLng = jest.fn();
const mockOpenPopup = jest.fn();
const mockPositions: unknown[] = [];
jest.mock("react-leaflet", () => {
  const React = require("react");
  const shape = (name: string) => (props: any) => (
    <div data-testid={name}>{props.children}</div>
  );
  return {
    Marker: React.forwardRef((props: any, ref: any) => {
      React.useImperativeHandle(ref, () => ({
        setLatLng: mockSetLatLng,
        openPopup: mockOpenPopup,
      }));
      mockPositions.push(props.position);
      return (
        <section data-testid="pin" data-icon={props.icon.options.html}>
          <button
            disabled={!props.draggable}
            onClick={() =>
              props.eventHandlers.dragend({
                target: { getLatLng: () => ({ lat: 43, lng: 44 }) },
              })
            }
          >
            Drag
          </button>
          {props.children}
        </section>
      );
    }),
    Popup: ({ children }: any) => <div>{children}</div>,
    Tooltip: ({ children }: any) => <div role="tooltip">{children}</div>,
    Polyline: shape("line"),
    Polygon: shape("area"),
  };
});

const point: SavedPointJs = {
  id: "point-1",
  name: "TARGET",
  kind: "target",
  position: { lat: 42, lng: 42 },
  coordinates: "42N 42E",
  altitude_ft: 123,
  heading_deg: 90,
  length_nm: 20,
  end: { lat: 42, lng: 42 },
};
const receiver: Receiver = {
  id: "flight-1",
  callsign: "Hawg",
  aircraft: "A-10C",
  departure: "Base",
  kinds: ["waypoint", "target"],
  room: { waypoint: 5 },
  points: [point],
  drawings: [],
};
const response = (body: unknown, ok = true) => ({ ok, json: async () => body });
function deferred() {
  let resolve!: (value: any) => void;
  const promise = new Promise<any>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
function changed(detail?: object) {
  window.dispatchEvent(new CustomEvent(CHANGED_EVENT, { detail }));
}

beforeEach(() => {
  jest.clearAllMocks();
  mockPositions.length = 0;
  global.fetch = jest.fn().mockResolvedValue(response([receiver]));
});

it("draws one pin, in its kind's colour, for a point two flights share", async () => {
  (fetch as jest.Mock).mockResolvedValue(
    response([receiver, { ...receiver, id: "flight-2", callsign: "Boar" }]),
  );
  render(<SavedPointsLayer />);
  expect(await screen.findAllByTestId("pin")).toHaveLength(1);
  expect(screen.getByRole("tooltip")).toHaveTextContent(
    "Hawg: TARGET (Target)",
  );
  expect(screen.getByTestId("pin").dataset.icon).toContain('fill="#E08A7A"');
  expect(pinIcon("waypoint").options.html).toContain('fill="#8FC3F0"');
  // The same object each time, or react-leaflet rebuilds the marker under a drag.
  expect(pinIcon("target")).toBe(pinIcon("target"));
});

it("keeps an orbit's dashed line and the drawings beside the pins", async () => {
  const orbit = { ...point, id: "orbit-1", name: "CAP", kind: "orbit" };
  const line = { name: "FLOT", closed: false, points: [point.position] };
  const area = { name: "KILLBOX", closed: true, points: [point.position] };
  (fetch as jest.Mock).mockResolvedValue(
    response([{ ...receiver, points: [point, orbit], drawings: [line, area] }]),
  );
  render(<SavedPointsLayer />);
  expect(await screen.findAllByTestId("pin")).toHaveLength(2);
  expect(screen.getAllByTestId("line")).toHaveLength(2);
  expect(screen.getAllByTestId("area")).toHaveLength(1);
  expect(screen.getByText("Orbit 090° for 20 NM")).toBeInTheDocument();
  expect(
    screen.getByText("Drag the pin to move this orbit."),
  ).toBeInTheDocument();
});

it("renames and deletes by the point's id and announces each edit", async () => {
  const notify = jest.fn();
  window.addEventListener(CHANGED_EVENT, notify);
  render(<SavedPointPin point={point} receiver={receiver} />);
  fireEvent.change(screen.getByLabelText("Name"), {
    target: { value: "BRIDGE" },
  });
  fireEvent.click(screen.getByText("Rename"));
  await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
  expect(fetch).toHaveBeenLastCalledWith(
    expect.stringContaining("saved-points/flight-1/points/point-1"),
    expect.objectContaining({
      method: "PATCH",
      body: JSON.stringify({ name: "BRIDGE" }),
    }),
  );
  fireEvent.click(screen.getByText("Delete"));
  await waitFor(() => expect(notify).toHaveBeenCalledTimes(2));
  expect(fetch).toHaveBeenLastCalledWith(
    expect.stringContaining("saved-points/flight-1/points/point-1"),
    expect.objectContaining({ method: "DELETE" }),
  );
  window.removeEventListener(CHANGED_EVENT, notify);
});

it("shows whose point it is, where, and how high", () => {
  render(<SavedPointPin point={point} receiver={receiver} />);
  expect(screen.getByText("Hawg · A-10C")).toBeInTheDocument();
  expect(screen.getByText("42N 42E · 123 ft")).toBeInTheDocument();
  expect(
    screen.getByText("Drag the pin to move this point."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("Moving it re-reads the ground elevation."),
  ).toBeInTheDocument();
});

it("shows no elevation for a point that has none", () => {
  // 0 is "none": what a drag leaves when the ground lookup fails.
  render(
    <SavedPointPin point={{ ...point, altitude_ft: 0 }} receiver={receiver} />,
  );
  expect(screen.getByText("42N 42E")).toBeInTheDocument();
  expect(screen.queryByText(/0 ft/)).not.toBeInTheDocument();
});

it("locks the pin during a move and puts it back when the move fails", async () => {
  const pending = deferred();
  (fetch as jest.Mock).mockReturnValue(pending.promise);
  render(<SavedPointPin point={point} receiver={receiver} />);
  fireEvent.click(screen.getByText("Drag"));
  expect(screen.getByText("Delete")).toBeDisabled();
  expect(screen.getByText("Drag")).toBeDisabled();
  expect(fetch).toHaveBeenLastCalledWith(
    expect.any(String),
    expect.objectContaining({
      method: "PATCH",
      body: JSON.stringify({ position: { lat: 43, lng: 44 } }),
    }),
  );
  await act(async () => {
    pending.resolve(response({ detail: "No such point" }, false));
  });
  expect(screen.getByRole("alert")).toHaveTextContent("No such point");
  expect(mockSetLatLng).toHaveBeenCalledWith(point.position);
  expect(mockOpenPopup).toHaveBeenCalled();
  expect(screen.getByText("Drag")).toBeEnabled();
});

it("says so plainly when the server's reason is not a sentence", async () => {
  (fetch as jest.Mock).mockResolvedValue(
    response({ detail: [{ msg: "Input should be less than 90" }] }, false),
  );
  render(<SavedPointPin point={point} receiver={receiver} />);
  fireEvent.click(screen.getByText("Drag"));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Could not update the point",
  );
});

it("redraws a renamed point and drops a deleted one", async () => {
  render(<SavedPointsLayer />);
  await screen.findByRole("tooltip");
  (fetch as jest.Mock).mockResolvedValue(
    response([{ ...receiver, points: [{ ...point, name: "NEW" }] }]),
  );
  act(() => changed());
  // The Name box follows the point in an effect, a render after the tooltip.
  await waitFor(() => {
    expect(screen.getByRole("tooltip")).toHaveTextContent("NEW");
    expect(screen.getByLabelText("Name")).toHaveValue("NEW");
  });
  (fetch as jest.Mock).mockResolvedValue(response([]));
  act(() => changed());
  await waitFor(() =>
    expect(screen.queryByTestId("pin")).not.toBeInTheDocument(),
  );
});

it("does not hand the marker a new position when a re-read finds it unmoved", async () => {
  render(<SavedPointsLayer />);
  await screen.findByTestId("pin");
  const first = mockPositions[0];
  const before = mockPositions.length;
  (fetch as jest.Mock).mockResolvedValue(
    response([
      { ...receiver, points: [{ ...point, position: { lat: 42, lng: 42 } }] },
    ]),
  );
  await act(async () => changed());
  await waitFor(() => expect(mockPositions.length).toBeGreaterThan(before));
  expect(mockPositions.every((one) => one === first)).toBe(true);
});

it("ignores an answer that arrives after a newer one was asked for", async () => {
  const old = deferred();
  (fetch as jest.Mock).mockReturnValueOnce(old.promise);
  render(<SavedPointsLayer />);
  (fetch as jest.Mock).mockResolvedValue(response([]));
  await act(async () => changed());
  await act(async () => old.resolve(response([receiver])));
  expect(screen.queryByTestId("pin")).not.toBeInTheDocument();
});

it.each(["unloaded", "reset"])(
  "clears the pins when the campaign is %s and ignores what was still on its way",
  async (event) => {
    render(<SavedPointsLayer />);
    await screen.findByTestId("pin");
    const old = deferred();
    (fetch as jest.Mock)
      .mockReturnValueOnce(old.promise)
      .mockResolvedValue(response([]));
    act(() => changed());
    await act(async () => changed({ [event]: true }));
    expect(screen.queryByTestId("pin")).not.toBeInTheDocument();
    await act(async () => old.resolve(response([receiver])));
    expect(screen.queryByTestId("pin")).not.toBeInTheDocument();
  },
);

it("keeps what is drawn when a re-read fails", async () => {
  render(<SavedPointsLayer />);
  await screen.findByTestId("pin");
  (fetch as jest.Mock).mockRejectedValue(new Error("offline"));
  await act(async () => changed());
  expect(screen.getByTestId("pin")).toBeInTheDocument();
});

it("still re-reads every few seconds when nothing announces a change", async () => {
  jest.useFakeTimers();
  try {
    render(<SavedPointsLayer />);
    await act(async () => {});
    expect(fetch).toHaveBeenCalledTimes(1);
    await act(async () => {
      jest.advanceTimersByTime(5000);
    });
    expect(fetch).toHaveBeenCalledTimes(2);
  } finally {
    jest.useRealTimers();
  }
});

it("stops listening, stops polling and aborts its request when it goes away", () => {
  jest.useFakeTimers();
  try {
    const pending = deferred();
    (fetch as jest.Mock).mockReturnValue(pending.promise);
    const view = render(<SavedPointsLayer />);
    const signal = (fetch as jest.Mock).mock.calls[0][1].signal;
    view.unmount();
    expect(signal.aborted).toBe(true);
    changed();
    jest.advanceTimersByTime(5000);
    expect(fetch).toHaveBeenCalledTimes(1);
  } finally {
    jest.useRealTimers();
  }
});
