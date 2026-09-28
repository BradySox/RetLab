/**
 * A shape's className has to reach the Leaflet constructor. react-leaflet hands
 * pathOptions to setStyle, and Leaflet writes className onto the path only when it
 * creates it -- so a class passed that way never reached the DOM, and the coordinate
 * picker went on ignoring clicks inside every country (§98's `map-area`).
 */
import { CasedCircle, CasedCircleMarker, CasedPolygon } from "./CasedShapes";
import { mapStrokes } from "../../theme/mapColors";
import { render } from "@testing-library/react";

const mockCreated: any[] = [];

jest.mock("react-leaflet", () => {
  const shape = (props: any) => {
    mockCreated.push(props);
    return null;
  };
  return { Circle: shape, CircleMarker: shape, Polygon: shape };
});

beforeEach(() => {
  mockCreated.length = 0;
});

const style = {
  color: "#ff0000",
  signature: mapStrokes.airspaceBelligerent,
  className: "map-area",
};

it.each([
  ["polygon", <CasedPolygon {...style} positions={[[0, 0], [1, 1], [1, 0]]} />],
  ["circle", <CasedCircle {...style} center={[0, 0]} radius={1000} />],
  ["circle marker", <CasedCircleMarker {...style} center={[0, 0]} radius={4} />],
])("the %s's top shape is created with the class", (_, shape) => {
  render(shape);
  const [casing, top] = mockCreated;
  expect(top.className).toBe("map-area");
  expect(casing.className).toBeUndefined();
});
