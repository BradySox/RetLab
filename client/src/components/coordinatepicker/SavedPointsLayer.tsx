// What the player has saved for their aircraft, drawn on the map (§102).
//
// Re-read after every save from the map and every few seconds otherwise, because the
// My aircraft window renames and deletes without telling the map.
import {
  CHANGED_EVENT,
  KIND_LABEL,
  Receiver,
  fetchReceivers,
} from "./receivers";
import { Fragment, useEffect, useState } from "react";
import {
  CircleMarker,
  Polygon,
  Polyline,
  Tooltip,
} from "react-leaflet";

const REFRESH_MS = 5000;

const COLOUR: Record<string, string> = {
  waypoint: "#8FC3F0",
  ip: "#86C39A",
  target: "#E08A7A",
  hold: "#C7B2F0",
  orbit: "#F0D08F",
  markpoint: "#E0A86B",
};
const DRAWING = "#FFFF66";

export default function SavedPointsLayer() {
  const [receivers, setReceivers] = useState<Receiver[]>([]);

  useEffect(() => {
    let dropped = false;
    const load = () => {
      fetchReceivers()
        .then((list) => {
          if (!dropped) {
            setReceivers(list);
          }
        })
        .catch(() => undefined);
    };
    load();
    const timer = window.setInterval(load, REFRESH_MS);
    window.addEventListener(CHANGED_EVENT, load);
    return () => {
      dropped = true;
      window.clearInterval(timer);
      window.removeEventListener(CHANGED_EVENT, load);
    };
  }, []);

  return (
    <>
      {receivers.map((receiver) => (
        <Fragment key={receiver.id}>
          {(receiver.points ?? []).map((point, index) => {
            const colour = COLOUR[point.kind] ?? COLOUR.waypoint;
            const label = `${receiver.callsign}: ${point.name} (${
              KIND_LABEL[point.kind] ?? point.kind
            })`;
            return (
              <Fragment key={`p${index}`}>
                <CircleMarker
                  center={point.position}
                  radius={6}
                  pathOptions={{ color: colour, weight: 2, fillOpacity: 0.4 }}
                >
                  <Tooltip>{label}</Tooltip>
                </CircleMarker>
                {point.kind === "orbit" && (
                  <Polyline
                    positions={[point.position, point.end]}
                    pathOptions={{ color: colour, weight: 3, dashArray: "8 6" }}
                  >
                    <Tooltip>{label}</Tooltip>
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
