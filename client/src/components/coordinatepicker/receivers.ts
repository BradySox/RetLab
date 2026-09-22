// The player's aircraft as the saved-points API describes them (§102).
import { HTTP_URL } from "../../api/backend";

export interface LatLngJs {
  lat: number;
  lng: number;
}

export interface SavedPointJs {
  kind: string;
  name: string;
  coordinates: string;
  altitude_ft: number;
  position: LatLngJs;
  heading_deg: number;
  length_nm: number;
  end: LatLngJs;
}

export interface SavedDrawingJs {
  name: string;
  points: LatLngJs[];
  closed: boolean;
}

export interface Receiver {
  id: string;
  callsign: string;
  aircraft: string;
  departure: string;
  kinds: string[];
  room: Record<string, number>;
  points?: SavedPointJs[];
  drawings?: SavedDrawingJs[];
  drawing_room?: number;
}

export const KIND_LABEL: Record<string, string> = {
  waypoint: "Waypoint",
  markpoint: "Markpoint",
  ip: "IP",
  target: "Target",
  hold: "Hold",
  orbit: "Orbit",
};

// Fired after anything is saved, so the map layer redraws without waiting.
export const CHANGED_EVENT = "retlab-saved-points-changed";

export function announceChange(): void {
  window.dispatchEvent(new Event(CHANGED_EVENT));
}

// Anything that is not a list of aircraft (an error page, an older server) reads as
// none, so a popup never throws inside a render.
export async function fetchReceivers(): Promise<Receiver[]> {
  const response = await fetch(`${HTTP_URL}saved-points/`);
  const body: unknown = response.ok ? await response.json() : null;
  return Array.isArray(body) ? (body as Receiver[]) : [];
}

export async function postJson(
  path: string,
  payload: unknown,
): Promise<{ ok: boolean; body: unknown }> {
  const response = await fetch(`${HTTP_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body: unknown = await response.json().catch(() => null);
  return { ok: response.ok, body };
}

export function detailOf(body: unknown, fallback: string): string {
  return body && typeof body === "object" && "detail" in body
    ? String((body as { detail: unknown }).detail)
    : fallback;
}
