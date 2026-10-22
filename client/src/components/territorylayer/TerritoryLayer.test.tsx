import { renderWithProviders } from "../../testutils";
import { SectorsLayer, TerritoryLayer } from "./TerritoryLayer";
import { PropsWithChildren } from "react";

const mockPolygon = jest.fn();
const mockPolyline = jest.fn();
const mockMarker = jest.fn();
let mockZoom = 8;
let mockCentered = true;
jest.mock("react-leaflet", () => ({
  LayerGroup: (props: PropsWithChildren<any>) => <>{props.children}</>,
  Pane: (props: PropsWithChildren<any>) => <>{props.children}</>,
  Polygon: (props: PropsWithChildren<any>) => {
    mockPolygon(props);
    return null;
  },
  Polyline: (props: PropsWithChildren<any>) => {
    mockPolyline(props);
    return null;
  },
  Marker: (props: PropsWithChildren<any>) => {
    mockMarker(props);
    return null;
  },
  useMap: () => ({
    getZoom: () => mockZoom,
    getBounds: () => {
      if (!mockCentered) throw new Error("Set map center and zoom first.");
      return { contains: () => true };
    },
  }),
  useMapEvents: () => null,
}));

const ring = [
  { lat: 0, lng: 0 },
  { lat: 0, lng: 1 },
  { lat: 1, lng: 1 },
];
const sectors = {
  edges: [ring],
  sectors: [
    { name: "WHISKEY-14", owner: "red", position: { lat: 0.5, lng: 0.5 } },
  ],
};

describe("TerritoryLayer", () => {
  beforeEach(() => {
    mockCentered = true;
    mockPolygon.mockClear();
    mockPolyline.mockClear();
    mockMarker.mockClear();
  });

  it("fills both sides", () => {
    renderWithProviders(<TerritoryLayer />, {
      preloadedState: {
        territory: {
          territory: { blue: [[ring]], red: [[ring], [ring]] },
          sectors: { edges: [], sectors: [] },
        },
      },
    });
    expect(mockPolygon).toHaveBeenCalledTimes(3);
  });

  it("hides sector names when zoomed out", () => {
    mockZoom = 8;
    renderWithProviders(<SectorsLayer />, {
      preloadedState: {
        territory: { territory: { blue: [], red: [] }, sectors: sectors },
      },
    });
    expect(mockPolyline).toHaveBeenCalledTimes(1);
    expect(mockMarker).not.toHaveBeenCalled();
  });

  it("names sectors when zoomed in", () => {
    mockZoom = 10;
    renderWithProviders(<SectorsLayer />, {
      preloadedState: {
        territory: { territory: { blue: [], red: [] }, sectors: sectors },
      },
    });
    expect(mockMarker).toHaveBeenCalledTimes(1);
  });

  it("draws before the map has a center", () => {
    mockZoom = 10;
    mockCentered = false;
    renderWithProviders(<SectorsLayer />, {
      preloadedState: {
        territory: { territory: { blue: [], red: [] }, sectors: sectors },
      },
    });
    expect(mockPolyline).toHaveBeenCalledTimes(1);
    expect(mockMarker).not.toHaveBeenCalled();
  });
});
