// Drawing a line or an area for one of the player's aircraft (§102).
//
// While it is open every click on bare map is a corner. It saves to the aircraft
// picked here, which puts the drawing on that jet's cartridge where it has room and on
// the kneeboard and map regardless.
import {
  Receiver,
  announceChange,
  detailOf,
  fetchReceivers,
  postJson,
} from "./receivers";
import L, { LatLng } from "leaflet";
import { useEffect, useRef, useState } from "react";

export default function DrawPanel(props: {
  points: LatLng[];
  undo: () => void;
  close: () => void;
}) {
  const [receivers, setReceivers] = useState<Receiver[]>([]);
  const [chosen, setChosen] = useState<string>("");
  const [name, setName] = useState<string>("");
  const [said, setSaid] = useState<string>("");
  const panel = useRef<HTMLDivElement | null>(null);

  // Clicks on the panel must not reach the map, or every button press is a corner.
  useEffect(() => {
    if (panel.current) {
      L.DomEvent.disableClickPropagation(panel.current);
      L.DomEvent.disableScrollPropagation(panel.current);
    }
  }, []);

  useEffect(() => {
    let dropped = false;
    fetchReceivers()
      .then((list) => {
        if (!dropped) {
          setReceivers(list);
          setChosen(list.length > 0 ? list[0].id : "");
        }
      })
      .catch(() => setReceivers([]));
    return () => {
      dropped = true;
    };
  }, []);

  const finish = async (closed: boolean) => {
    if (chosen === "") {
      return;
    }
    const { ok, body } = await postJson(`saved-points/${chosen}/drawings`, {
      name: name,
      closed: closed,
      points: props.points.map((p) => ({ lat: p.lat, lng: p.lng })),
    });
    if (!ok) {
      setSaid(detailOf(body, "Could not save it"));
      return;
    }
    announceChange();
    props.close();
  };

  const count = props.points.length;
  return (
    <div className="cp-draw" ref={panel}>
      <div className="cp-draw-title">
        Drawing · {count} {count === 1 ? "corner" : "corners"}
      </div>
      <div className="cp-draw-hint">Click the map to add a corner.</div>
      {receivers.length === 0 ? (
        <div className="cp-save-none">No player aircraft to save to</div>
      ) : (
        <select value={chosen} onChange={(e) => setChosen(e.target.value)}>
          {receivers.map((one) => (
            <option key={one.id} value={one.id}>
              {one.callsign} · {one.aircraft}
            </option>
          ))}
        </select>
      )}
      <input
        placeholder="Name (optional)"
        maxLength={24}
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <div className="cp-save-buttons">
        <button disabled={count < 2 || chosen === ""} onClick={() => finish(false)}>
          Save line
        </button>
        <button disabled={count < 3 || chosen === ""} onClick={() => finish(true)}>
          Save area
        </button>
        <button disabled={count === 0} onClick={props.undo}>
          Undo
        </button>
        <button onClick={props.close}>Cancel</button>
      </div>
      {said !== "" && <div className="cp-save-said">{said}</div>}
    </div>
  );
}
