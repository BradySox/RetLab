// A refused route edit is said on the map, where it was tried, not in the console.
import L, { LatLngExpression, Map } from "leaflet";

export function showNotice(map: Map, at: LatLngExpression, text: string): void {
  const box = L.DomUtil.create("div", "route-notice");
  // Text, not HTML: the reason names waypoints, and a custom name is typed by a player.
  box.textContent = text;
  L.popup({ autoPan: false }).setLatLng(at).setContent(box).openOn(map);
}

// RTK Query's unwrap() rejects with the server's body as `data`; a 409 carries the
// reason in `detail`.
export function refusal(error: unknown, fallback: string): string {
  const detail = (error as { data?: { detail?: unknown } } | null)?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}
