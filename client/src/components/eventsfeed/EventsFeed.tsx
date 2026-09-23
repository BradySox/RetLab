import { selectCampaignStatus } from "../../api/campaignStatusSlice";
import { useAppSelector } from "../../app/hooks";
import "./EventsFeed.css";
import { useState } from "react";

// The turn-events feed (item-5 UI): the campaign's Information messages —
// phase transitions, ROE violations, political-will moves, exhaustion banners —
// surfaced on the map instead of living only in the Qt log. Collapsed to a
// count chip by default; renders nothing when there are no recent events.
// A plain positioned div, not a Leaflet layer.

// Upstream's "Game Start" and "End of turn #N" carry a rule of 40 hyphens as
// their body (game/game.py); a body with no letter or digit is decoration.
export function hasContent(text: string | null | undefined): boolean {
  return !!text && /[\p{L}\p{N}]/u.test(text);
}

export default function EventsFeed() {
  const status = useAppSelector(selectCampaignStatus);
  const [open, setOpen] = useState(false);
  const events = status?.events ?? [];
  if (events.length === 0) {
    return null;
  }
  return (
    <div className="events-feed">
      <div className="events-feed-chip" onClick={() => setOpen(!open)}>
        Events ({events.length}) {open ? "▾" : "▴"}
      </div>
      {open && (
        <div className="events-feed-list">
          {events.map((event, idx) => (
            <div className="events-feed-entry" key={idx}>
              <div className="events-feed-title">
                <span className="events-feed-turn">T{event.turn}</span>
                {event.title}
              </div>
              {hasContent(event.text) && (
                <div className="events-feed-text">{event.text}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
