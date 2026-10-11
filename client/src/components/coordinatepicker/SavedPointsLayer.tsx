// What the player has saved for their aircraft, drawn on the map (§102).
//
// Re-read when the server or the map says something changed, and every few seconds
// as a fallback for a change neither of them announced.
import SavedPointPin, { colourOf, labelOf } from "./SavedPointPin";
import {
  CHANGED_EVENT,
  ChangeDetail,
  Receiver,
  fetchReceivers,
} from "./receivers";
import { Fragment, useEffect, useState } from "react";
import { Polygon, Polyline, Tooltip } from "react-leaflet";

const REFRESH_MS = 5000;

const DRAWING = "#FFFF66";

export default function SavedPointsLayer() {
  const [receivers, setReceivers] = useState<Receiver[]>([]);

  useEffect(() => {
    let generation = 0;
    let dropped = false;
    let controller: AbortController | undefined;
    const load = async (event?: Event) => {
      // Only the newest request may draw: an older answer can arrive after it.
      const request = ++generation;
      controller?.abort();
      controller = new AbortController();
      const detail = (event as CustomEvent<ChangeDetail> | undefined)?.detail;
      if (detail?.reset || detail?.unloaded) {
        setReceivers([]);
      }
      if (detail?.unloaded) {
        return;
      }
      try {
        const list = await fetchReceivers(controller.signal);
        if (!dropped && request === generation) {
          setReceivers(list);
        }
      } catch {
        // What is drawn stays; the next read asks again.
      }
    };
    void load();
    const timer = window.setInterval(() => void load(), REFRESH_MS);
    window.addEventListener(CHANGED_EVENT, load);
    return () => {
      dropped = true;
      controller?.abort();
      window.clearInterval(timer);
      window.removeEventListener(CHANGED_EVENT, load);
    };
  }, []);

  // Flights of one squadron share its points, so each is drawn once.
  const seen = new Set<string>();
  return (
    <>
      {receivers.map((receiver) => (
        <Fragment key={receiver.id}>
          {(receiver.points ?? []).map((point) => {
            if (!point.id || !point.position || seen.has(point.id)) {
              return null;
            }
            seen.add(point.id);
            return (
              <Fragment key={point.id}>
                <SavedPointPin receiver={receiver} point={point} />
                {point.kind === "orbit" && (
                  <Polyline
                    positions={[point.position, point.end]}
                    pathOptions={{
                      color: colourOf(point.kind),
                      weight: 3,
                      dashArray: "8 6",
                    }}
                  >
                    <Tooltip>{labelOf(receiver, point)}</Tooltip>
                  </Polyline>
                )}
              </Fragment>
            );
          })}
          {(receiver.drawings ?? []).map((drawing, index) => {
            const label = `${receiver.callsign}: ${drawing.name}`;
            return drawing.closed ? (
              <Polygon
                key={`d${index}`}
                positions={drawing.points}
                pathOptions={{ color: DRAWING, weight: 2, fillOpacity: 0.08 }}
              >
                <Tooltip>{label}</Tooltip>
              </Polygon>
            ) : (
              <Polyline
                key={`d${index}`}
                positions={drawing.points}
                pathOptions={{ color: DRAWING, weight: 2 }}
              >
                <Tooltip>{label}</Tooltip>
              </Polyline>
            );
          })}
        </Fragment>
      ))}
    </>
  );
}
