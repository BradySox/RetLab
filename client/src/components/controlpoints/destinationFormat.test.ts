import { formatLatLng } from "./destinationFormat";
import { LatLng } from "leaflet";

describe("formatLatLng", () => {
  it("drops the minus sign in the southern and western hemispheres", () => {
    expect(formatLatLng(new LatLng(-51.7, -58.1))).toBe(
      "51.70&deg;S 58.10&deg;W"
    );
  });

  it("formats the northern and eastern hemispheres", () => {
    expect(formatLatLng(new LatLng(36.2, 115.3))).toBe(
      "36.20&deg;N 115.30&deg;E"
    );
  });
});
