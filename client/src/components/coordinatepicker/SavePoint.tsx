// Putting the picked point into one of the player's own aircraft.
//
// Ported from juanjux/dcs-escalation (LGPL-3.0). The kind picker, the orbit's heading
// and length, and "Draw from here" are §102.
//
// Only aircraft somebody is actually sitting in are offered, and only the kinds the
// server says that airframe can be handed: a kind that would never reach the cockpit
// is not a button.
import {
  KIND_LABEL,
  Receiver,
  announceChange,
  detailOf,
  fetchReceivers,
  postJson,
} from "./receivers";
import { LatLng } from "leaflet";
import { useEffect, useState } from "react";

// The kind inside a sentence: "waypoint", but "IP".
function kindWord(kind: string): string {
  const label = KIND_LABEL[kind] ?? kind;
  return label === label.toUpperCase() ? label : label.toLowerCase();
}

export default function SavePoint(props: {
  at: LatLng;
  name: string;
  elevationFt?: number;
  onDraw?: () => void;
}) {
  const [receivers, setReceivers] = useState<Receiver[] | null>(null);
  const [chosen, setChosen] = useState<string>("");
  const [kind, setKind] = useState<string>("");
  const [said, setSaid] = useState<string>("");
  // A weapon aimed at a saved point from the wrong elevation lands short or long.
  const [feet, setFeet] = useState<string>(
    props.elevationFt === undefined ? "" : String(props.elevationFt),
  );
  const [heading, setHeading] = useState<string>("90");
  const [length, setLength] = useState<string>("20");

  useEffect(() => {
    let dropped = false;
    (async () => {
      try {
        const list = await fetchReceivers();
        if (dropped) {
          return;
        }
        setReceivers(list);
        setChosen(list.length > 0 ? list[0].id : "");
      } catch (error) {
        console.error("Could not list the player's aircraft", error);
        setReceivers([]);
      }
    })();
    return () => {
      dropped = true;
    };
  }, []);

  if (receivers === null) {
    return null;
  }
  if (receivers.length === 0) {
    return (
      <div className="cp-save cp-save-none">No player aircraft to save to</div>
    );
  }

  const receiver = receivers.find((one) => one.id === chosen) ?? receivers[0];
  const kinds = receiver.kinds ?? [];
  const current = kinds.includes(kind) ? kind : kinds[0] ?? "";
  const room = receiver.room?.[current] ?? 0;

  const save = async () => {
    setSaid("");
    try {
      const { ok, body } = await postJson(`saved-points/${receiver.id}`, {
        kind: current,
        name: props.name,
        lat: props.at.lat,
        lng: props.at.lng,
        altitude_ft: Math.max(0, Math.round(Number(feet) || 0)),
        heading_deg: Math.round(Number(heading) || 0),
        length_nm: Math.max(1, Number(length) || 20),
      });
      if (!ok) {
        setSaid(detailOf(body, "Could not save it"));
        return;
      }
      const updated = body as Receiver | null;
      announceChange();
      if (!updated || typeof updated.id !== "string") {
        setSaid("Saved");
        return;
      }
      setReceivers(
        receivers.map((one) => (one.id === updated.id ? updated : one)),
      );
      setSaid(`Saved to ${updated.callsign}`);
    } catch (error) {
      console.error("Could not save the point", error);
      setSaid("Could not save it");
    }
  };

  return (
    <div className="cp-save">
      <select value={receiver.id} onChange={(e) => setChosen(e.target.value)}>
        {receivers.map((one) => (
          <option
            key={one.id}
            value={one.id}
            title={`${one.callsign} · ${one.aircraft} · from ${one.departure}`}
          >
            {one.callsign} · {one.aircraft}
          </option>
        ))}
      </select>
      {kinds.length > 1 && (
        <select
          className="cp-save-kind"
          value={current}
          onChange={(e) => setKind(e.target.value)}
        >
          {kinds.map((one) => (
            <option key={one} value={one}>
              {KIND_LABEL[one] ?? one}
            </option>
          ))}
        </select>
      )}
      <label className="cp-save-alt">
        Elevation
        {props.elevationFt === undefined ? "" : " (ground)"}
        <input
          type="number"
          min={0}
          step={100}
          value={feet}
          placeholder="0"
          onChange={(e) => setFeet(e.target.value)}
        />
        ft
      </label>
      {current === "orbit" && (
        <label className="cp-save-alt">
          Heading
          <input
            type="number"
            min={0}
            max={359}
            value={heading}
            onChange={(e) => setHeading(e.target.value)}
          />
          ° for
          <input
            type="number"
            min={1}
            value={length}
            onChange={(e) => setLength(e.target.value)}
          />
          NM
        </label>
      )}
      <div className="cp-save-buttons">
        {current !== "" && (
          <button
            disabled={room <= 0}
            title={
              room > 0
                ? `Room for ${room} more`
                : `${receiver.callsign} has no room for another`
            }
            onClick={save}
          >
            Save as {kindWord(current)}
          </button>
        )}
        {props.onDraw && (
          <button title="Click the map to add corners" onClick={props.onDraw}>
            Draw from here
          </button>
        )}
      </div>
      {said !== "" && <div className="cp-save-said">{said}</div>}
    </div>
  );
}
