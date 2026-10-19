import { Flight } from "../../api/liberationApi";
import { selectFlight, selectFlights } from "../../api/flightsSlice";
import { useAppDispatch, useAppSelector } from "../../app/hooks";

interface PackageGroup {
  target: string;
  tot: string;
  flights: Flight[];
}

export function groupByPackage(flights: Flight[]): PackageGroup[] {
  const groups = new Map<string, PackageGroup>();
  for (const flight of flights) {
    const target = flight.package_target ?? "";
    const tot = flight.package_tot ?? "";
    const key = `${tot}|${target}`;
    if (!groups.has(key)) {
      groups.set(key, { target, tot, flights: [] });
    }
    groups.get(key)!.flights.push(flight);
  }
  return Array.from(groups.values()).sort((a, b) =>
    a.tot === b.tot ? a.target.localeCompare(b.target) : a.tot.localeCompare(b.tot)
  );
}

interface FlightsTabProps {
  onShowOnMap: () => void;
}

export default function FlightsTab(props: FlightsTabProps) {
  const dispatch = useAppDispatch();
  const { flights, selected } = useAppSelector(selectFlights);
  const groups = groupByPackage(Object.values(flights).filter((f) => f.blue));
  if (groups.length === 0) {
    return <div className="phone-empty">No flights planned yet.</div>;
  }
  return (
    <div className="phone-list">
      {groups.map((group) => (
        <section key={`${group.tot}|${group.target}`} className="phone-package">
          <h2>
            {group.target || "No target"}
            {group.tot && <span className="phone-tot">TOT {group.tot}</span>}
          </h2>
          {group.flights.map((flight) => (
            <button
              type="button"
              key={flight.id}
              className={
                "phone-flight" + (flight.id === selected ? " selected" : "")
              }
              onClick={() => {
                dispatch(selectFlight(flight.id));
                props.onShowOnMap();
              }}
            >
              <span className="phone-flight-name">
                {flight.callsign
                  ? `${flight.callsign} · ${flight.flight_type}`
                  : flight.flight_type}
              </span>
              <span className="phone-flight-detail">
                {flight.num_aircraft ?? 1} x {flight.aircraft}
              </span>
            </button>
          ))}
        </section>
      ))}
    </div>
  );
}
