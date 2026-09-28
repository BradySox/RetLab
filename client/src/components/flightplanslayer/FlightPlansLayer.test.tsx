import { renderWithProviders } from "../../testutils";
import FlightPlansLayer from "./FlightPlansLayer";
import { waitFor } from "@testing-library/react";
import L from "leaflet";
import { PropsWithChildren } from "react";

const mockPolyline = jest.fn();
const mockLayerGroup = jest.fn();
// A refused edit is said in a popup on the map; these stand in for both.
const mockMap = {};
const mockShowNotice = jest.fn();
jest.mock("../waypointmarker/notice", () => ({
  ...jest.requireActual("../waypointmarker/notice"),
  showNotice: (...args: unknown[]) => mockShowNotice(...args),
}));
jest.mock("react-leaflet", () => ({
  LayerGroup: (props: PropsWithChildren<any>) => {
    mockLayerGroup(props);
    return <>{props.children}</>;
  },
  Polyline: require("react").forwardRef((props: any, _ref: any) => {
    mockPolyline(props);
    return null;
  }),
  useMap: () => mockMap,
}));

// The waypoints in test data below should all use `should_make: false`. Markers
// need useMap() to check the zoom level to decide if they should be drawn or
// not, and we don't have good options here for mocking that behavior.
describe("FlightPlansLayer", () => {
  describe("unselected flights", () => {
    it("are drawn", () => {
      renderWithProviders(<FlightPlansLayer blue={true} />, {
        preloadedState: {
          flights: {
            flights: {
              foo: {
                id: "foo",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
              bar: {
                id: "bar",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
            },
            selected: null,
          },
        },
      });

      // Each drawn blue flight renders two polylines now: the visible route and
      // a wide invisible hover overlay. Passing a ref to the visible one also
      // Each flight path includes multiple polyline segments.
      expect(mockPolyline).toHaveBeenCalledTimes(4);
      expect(mockLayerGroup).toBeCalledTimes(1);
    });
    it("are not drawn if wrong coalition", () => {
      renderWithProviders(<FlightPlansLayer blue={true} />, {
        preloadedState: {
          flights: {
            flights: {
              foo: {
                id: "foo",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
              bar: {
                id: "bar",
                blue: false,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
            },
            selected: null,
          },
        },
      });
      expect(mockPolyline).toHaveBeenCalledTimes(2);
      expect(mockLayerGroup).toBeCalledTimes(1);
    });
    it("are not drawn when only selected flights are to be drawn", () => {
      renderWithProviders(<FlightPlansLayer selectedOnly />, {
        preloadedState: {
          flights: {
            flights: {
              foo: {
                id: "foo",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
            },
            selected: null,
          },
        },
      });
      expect(mockPolyline).not.toHaveBeenCalled();
      expect(mockLayerGroup).toBeCalledTimes(1);
    });
  });
  describe("selected flights", () => {
    it("are drawn", () => {
      renderWithProviders(<FlightPlansLayer blue={true} />, {
        preloadedState: {
          flights: {
            flights: {
              foo: {
                id: "foo",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
              bar: {
                id: "bar",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
            },
            selected: "foo",
          },
        },
      });
      expect(mockPolyline).toHaveBeenCalledTimes(4);
      expect(mockLayerGroup).toBeCalledTimes(1);
    });
    it("are not drawn twice", () => {
      renderWithProviders(<FlightPlansLayer blue={true} />, {
        preloadedState: {
          flights: {
            flights: {
              foo: {
                id: "foo",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
            },
            selected: "foo",
          },
        },
      });
      expect(mockPolyline).toHaveBeenCalledTimes(2);
      expect(mockLayerGroup).toBeCalledTimes(1);
    });
    it("are not drawn if red", () => {
      renderWithProviders(<FlightPlansLayer selectedOnly />, {
        preloadedState: {
          flights: {
            flights: {
              foo: {
                id: "foo",
                blue: false,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
            },
            selected: "foo",
          },
        },
      });
      expect(mockPolyline).toHaveBeenCalled();
      expect(mockLayerGroup).toBeCalledTimes(1);
    });
  });
  it("are not drawn if there are no flights", () => {
    renderWithProviders(<FlightPlansLayer blue={true} />);
    expect(mockPolyline).not.toHaveBeenCalled();
    expect(mockLayerGroup).toBeCalledTimes(1);
  });
});

// A double-click on the selected route adds a point there (the server picks the
// leg); on any other route it does nothing, so the map still zooms.
describe("double-clicking a route", () => {
  const waypoint = (lat: number) => ({
    name: "",
    position: { lat: lat, lng: lat },
    altitude_ft: 0,
    altitude_reference: "MSL",
    is_movable: true,
    should_mark: false,
    include_in_path: true,
    timing: "",
  });
  const state = (selected: string | null) => ({
    preloadedState: {
      flights: {
        flights: {
          foo: {
            id: "foo",
            blue: true,
            sidc: "",
            waypoints: [waypoint(0), waypoint(1)],
          },
        },
        selected: selected,
      },
    },
  });
  const doubleClick = () => {
    const hitLine = mockPolyline.mock.calls
      .map(([props]) => props)
      .find((props) => props.eventHandlers?.dblclick);
    hitLine.eventHandlers.dblclick({
      latlng: { lat: 0.5, lng: 0.5 },
      originalEvent: {},
    });
  };

  const realFetch = global.fetch;
  beforeEach(() => {
    mockPolyline.mockClear();
    mockShowNotice.mockClear();
    global.fetch = jest
      .fn()
      .mockRejectedValue(new Error("offline")) as unknown as typeof fetch;
  });
  afterEach(() => {
    global.fetch = realFetch;
    jest.restoreAllMocks();
  });

  it("asks the server for a point on the selected route", async () => {
    const stop = jest.spyOn(L.DomEvent, "stopPropagation");
    renderWithProviders(<FlightPlansLayer blue={true} />, state("foo"));
    doubleClick();
    expect(stop).toHaveBeenCalled();
    // RTK Query sends it on the next tick.
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    // The request fails here, and the failure is said on the map, where it was.
    await waitFor(() =>
      expect(mockShowNotice).toHaveBeenCalledWith(
        mockMap,
        { lat: 0.5, lng: 0.5 },
        "Could not add a point here",
      ),
    );
  });

  it("leaves a route that is not selected alone", () => {
    const stop = jest.spyOn(L.DomEvent, "stopPropagation");
    renderWithProviders(<FlightPlansLayer blue={true} />, state(null));
    doubleClick();
    expect(stop).not.toHaveBeenCalled();
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
