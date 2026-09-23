import { LatLng } from "leaflet";

// Shared by the carrier (MobileControlPoint) and ship (MobileTgo) drag tooltips.

export function metersToNauticalMiles(meters: number): number {
  return meters * 0.000539957;
}

export function formatLatLng(latLng: LatLng): string {
  // The hemisphere suffix carries the sign: "32.50°S", not "-32.50°S".
  const lat = Math.abs(latLng.lat).toFixed(2);
  const lng = Math.abs(latLng.lng).toFixed(2);
  const ns = latLng.lat >= 0 ? "N" : "S";
  const ew = latLng.lng >= 0 ? "E" : "W";
  return `${lat}&deg;${ns} ${lng}&deg;${ew}`;
}
