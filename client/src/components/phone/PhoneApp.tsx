import CampaignStatusBar from "../campaignstatus";
import LiberationMap from "../liberationmap";
import FlightsTab from "./FlightsTab";
import PagesTab from "./PagesTab";
import "./PhoneApp.css";
import { useState } from "react";

type Tab = "map" | "flights" | "pages";

const TABS: { tab: Tab; label: string }[] = [
  { tab: "map", label: "Map" },
  { tab: "flights", label: "Flights" },
  { tab: "pages", label: "Kneeboards" },
];

/** The phone layout (§115): the map stays mounted under the other tabs. */
export default function PhoneApp() {
  const [tab, setTab] = useState<Tab>("map");
  return (
    <div className="App phone-app">
      <div className="phone-map">
        <CampaignStatusBar />
        <LiberationMap />
      </div>
      {tab !== "map" && (
        <div className="phone-panel">
          {tab === "flights" && <FlightsTab onShowOnMap={() => setTab("map")} />}
          {tab === "pages" && <PagesTab />}
        </div>
      )}
      <nav className="phone-tabs">
        {TABS.map((entry) => (
          <button
            type="button"
            key={entry.tab}
            className={entry.tab === tab ? "active" : ""}
            onClick={() => setTab(entry.tab)}
          >
            {entry.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
