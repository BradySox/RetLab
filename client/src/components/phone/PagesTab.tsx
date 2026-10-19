import backend, { HTTP_URL, withToken } from "../../api/backend";
import { useEffect, useState } from "react";

interface MissionPages {
  generated_at: string | null;
  decks: { name: string; page_count: number }[];
  has_briefing: boolean;
}

function pageUrl(path: string, stamp: string | null): string {
  const url = withToken(`${HTTP_URL}mission-pages/${path}`);
  return stamp ? `${url}&v=${encodeURIComponent(stamp)}` : url;
}

export default function PagesTab() {
  const [pages, setPages] = useState<MissionPages | null>(null);
  const [failed, setFailed] = useState(false);
  const [deck, setDeck] = useState<number | null>(null);

  useEffect(() => {
    backend
      .get<MissionPages>("mission-pages/")
      .then((response) => setPages(response.data))
      .catch(() => setFailed(true));
  }, []);

  if (failed) {
    return <div className="phone-empty">Could not reach Retribution.</div>;
  }
  if (pages == null) {
    return <div className="phone-empty">Loading...</div>;
  }
  if (pages.decks.length === 0 && !pages.has_briefing) {
    return (
      <div className="phone-empty">
        No mission generated yet. Press Take Off in Retribution first.
      </div>
    );
  }
  const stamp = pages.generated_at;
  if (deck != null && deck < pages.decks.length) {
    const chosen = pages.decks[deck];
    return (
      <div className="phone-deck">
        <button type="button" className="phone-back" onClick={() => setDeck(null)}>
          ‹ {chosen.name}
        </button>
        <div className="phone-pages">
          {Array.from({ length: chosen.page_count }, (_, page) => (
            <img
              key={page}
              src={pageUrl(`kneeboard/${deck}/${page}`, stamp)}
              alt={`${chosen.name} page ${page + 1}`}
              loading="lazy"
            />
          ))}
        </div>
      </div>
    );
  }
  return (
    <div className="phone-list">
      {stamp && <div className="phone-note">Generated {stamp.replace("T", " ")}</div>}
      {pages.has_briefing && (
        <section className="phone-package">
          <h2>Briefing</h2>
          <img
            className="phone-briefing"
            src={pageUrl("briefing", stamp)}
            alt="Briefing screen"
          />
        </section>
      )}
      {pages.decks.length > 0 && (
        <section className="phone-package">
          <h2>Kneeboards</h2>
          {pages.decks.map((d, index) => (
            <button
              type="button"
              key={d.name}
              className="phone-flight"
              onClick={() => setDeck(index)}
            >
              <span className="phone-flight-name">{d.name}</span>
              <span className="phone-flight-detail">{d.page_count} pages</span>
            </button>
          ))}
        </section>
      )}
    </div>
  );
}
