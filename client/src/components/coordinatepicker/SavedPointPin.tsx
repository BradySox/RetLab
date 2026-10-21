// One saved point's pin on the map (§102): hover for its name, click to rename or
// delete it, drag to move it.
//
// Ported from juanjux/dcs-escalation (LGPL-3.0). The pin is filled with its kind's
// colour, and an orbit's pin moves the whole racetrack.
import { HTTP_URL, withToken } from "../../api/backend";
import "./SavedPointPin.css";
import {
  KIND_LABEL,
  Receiver,
  SavedPointJs,
  announceChange,
} from "./receivers";
import L, { DivIcon, Marker as LeafletMarker } from "leaflet";
import { useEffect, useMemo, useRef, useState } from "react";
import { Marker, Popup, Tooltip } from "react-leaflet";

const COLOUR: Record<string, string> = {
  waypoint: "#8FC3F0",
  ip: "#86C39A",
  target: "#E08A7A",
  hold: "#C7B2F0",
  orbit: "#F0D08F",
  markpoint: "#E0A86B",
};
const OUTLINE = "#1D2731";
const FAILED = "Could not update the point";

export function colourOf(kind: string): string {
  return COLOUR[kind] ?? COLOUR.waypoint;
}

// One icon per colour, kept: react-leaflet rebuilds the marker's element whenever it
// is handed a new icon object, and that would drop a drag in progress.
const ICONS: Record<string, DivIcon> = {};

export function pinIcon(kind: string): DivIcon {
  const fill = colourOf(kind);
  if (!ICONS[fill]) {
    ICONS[fill] = L.divIcon({
      className: "saved-point-pin",
      html:
        '<svg viewBox="0 0 25 41" xmlns="http://www.w3.org/2000/svg">' +
        '<path d="M12.5 40C10 33 1 24 1 13a11.5 11.5 0 0 1 23 0c0 11-9 20-11.5 27Z"' +
        ` fill="${fill}" stroke="${OUTLINE}" stroke-width="1.5"/>` +
        `<circle cx="12.5" cy="13" r="4" fill="#FFFFFF" stroke="${OUTLINE}"/></svg>`,
      iconSize: [25, 41],
      iconAnchor: [12.5, 41],
      popupAnchor: [0, -35],
      tooltipAnchor: [12, -25],
    });
  }
  return ICONS[fill];
}

export function labelOf(receiver: Receiver, point: SavedPointJs): string {
  return `${receiver.callsign}: ${point.name} (${
    KIND_LABEL[point.kind] ?? point.kind
  })`;
}

async function mutate(
  receiver: Receiver,
  point: SavedPointJs,
  method: string,
  body?: object,
) {
  const response = await fetch(
    withToken(`${HTTP_URL}saved-points/${receiver.id}/points/${point.id}`),
    {
      method,
      headers: { "Content-Type": "application/json" },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    },
  );
  if (!response.ok) {
    // A validation error's detail is a list, which is no use to the reader.
    const result = await response.json().catch(() => null);
    throw new Error(
      typeof result?.detail === "string" ? result.detail : FAILED,
    );
  }
  announceChange();
}

export default function SavedPointPin({
  receiver,
  point,
}: {
  receiver: Receiver;
  point: SavedPointJs;
}) {
  const marker = useRef<LeafletMarker | null>(null);
  const input = useRef<HTMLInputElement | null>(null);
  const [name, setName] = useState(point.name);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => setName(point.name), [point.name]);

  // The same object until the point really moves: the layer re-reads every few
  // seconds, and a new object each time would snap a pin back mid-drag.
  const { lat, lng } = point.position;
  const position = useMemo(() => ({ lat, lng }), [lat, lng]);

  const change = async (method: string, body?: object) => {
    setBusy(true);
    setError("");
    try {
      await mutate(receiver, point, method, body);
    } catch (failure) {
      marker.current?.setLatLng(position);
      setError(failure instanceof Error ? failure.message : FAILED);
      marker.current?.openPopup();
    } finally {
      setBusy(false);
    }
  };

  const orbit = point.kind === "orbit";
  return (
    <Marker
      ref={marker}
      position={position}
      icon={pinIcon(point.kind)}
      draggable={!busy}
      bubblingMouseEvents={false}
      eventHandlers={{
        dragend: (event) => {
          const at = (event.target as LeafletMarker).getLatLng();
          void change("PATCH", { position: { lat: at.lat, lng: at.lng } });
        },
        popupopen: () => {
          input.current?.focus();
          input.current?.select();
        },
      }}
    >
      <Tooltip>{labelOf(receiver, point)}</Tooltip>
      <Popup autoPan={false}>
        <form
          className="saved-point-editor"
          onSubmit={(event) => {
            event.preventDefault();
            if (!busy && name.trim()) {
              void change("PATCH", { name });
            }
          }}
        >
          <label>
            Name
            <input
              ref={input}
              value={name}
              maxLength={24}
              disabled={busy}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <div className="saved-point-owner">
            {receiver.callsign} · {receiver.aircraft}
          </div>
          <div>
            {point.coordinates}
            {point.altitude_ft ? ` · ${point.altitude_ft} ft` : ""}
          </div>
          {orbit && (
            <div>
              Orbit {String(point.heading_deg).padStart(3, "0")}° for{" "}
              {point.length_nm} NM
            </div>
          )}
          <div className="saved-point-buttons">
            <button type="submit" disabled={busy || !name.trim()}>
              Rename
            </button>
            <button
              type="button"
              disabled={busy}
              className="saved-point-delete"
              onClick={() => void change("DELETE")}
            >
              Delete
            </button>
          </div>
          <div className="saved-point-hint">
            Drag the pin to move this {orbit ? "orbit" : "point"}.
          </div>
          <div className="saved-point-hint">
            Moving it re-reads the ground elevation.
          </div>
          {error && <div role="alert">{error}</div>}
        </form>
      </Popup>
    </Marker>
  );
}
