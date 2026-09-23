import { renderWithProviders } from "../../testutils";
import FrontMovementLayer from "./FrontMovementLayer";
import { PropsWithChildren } from "react";

const mockPolyline = jest.fn();
jest.mock("react-leaflet", () => ({
  LayerGroup: (props: PropsWithChildren<any>) => <>{props.children}</>,
  Polyline: (props: PropsWithChildren<any>) => {
    mockPolyline(props);
    return <>{props.children}</>;
  },
  Tooltip: () => null,
}));

const extents = [
  { lat: 0, lng: 0 },
  { lat: 1, lng: 1 },
];
const shaft = [
  { lat: 0.5, lng: 0.4 },
  { lat: 0.5, lng: 0.6 },
];
const head = [
  { lat: 0.55, lng: 0.55 },
  { lat: 0.5, lng: 0.6 },
  { lat: 0.45, lng: 0.55 },
];

describe("FrontMovementLayer", () => {
  beforeEach(() => mockPolyline.mockClear());

  it("draws nothing for a front that held", () => {
    renderWithProviders(<FrontMovementLayer />, {
      preloadedState: {
        frontLines: { fronts: { foo: { id: "foo", extents: extents } } },
      },
    });
    expect(mockPolyline).not.toHaveBeenCalled();
  });

  it("draws a cased shaft and head for a front that moved", () => {
    renderWithProviders(<FrontMovementLayer />, {
      preloadedState: {
        frontLines: {
          fronts: {
            foo: {
              id: "foo",
              extents: extents,
              movement: {
                advancing_side: "blue",
                distance_nm: 2.7,
                toward: "Redburg",
                blue_stance: "Aggressive",
                shaft: shaft,
                head: head,
              },
            },
          },
        },
      },
    });
    // Casing + colour, for the shaft and the head.
    expect(mockPolyline).toHaveBeenCalledTimes(4);
    expect(mockPolyline).toHaveBeenCalledWith(
      expect.objectContaining({ positions: shaft })
    );
    expect(mockPolyline).toHaveBeenCalledWith(
      expect.objectContaining({ positions: head })
    );
  });
});
