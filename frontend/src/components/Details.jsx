import { zoneSummary } from "../lib/guidance.js";

/** Helper and demo view: zones, speed numbers and the spoken history. */
export function Details({ detections, stats, log, health }) {
  const zones = zoneSummary(detections);
  return (
    <aside className="details" aria-label="Details">
      <div className="zones">
        {["left", "ahead", "right"].map((zone) => {
          const d = zones[zone];
          return (
            <div key={zone} className={`zone ${d ? d.proximity : ""}`}>
              <small>{zone}</small>
              <b>{d ? `${d.label}${d.approaching ? " (approaching)" : ""}` : "Clear"}</b>
            </div>
          );
        })}
      </div>

      <div className="stats">
        <div><b>{stats.fps}</b><span>FPS</span></div>
        <div><b>{stats.modelMs}</b><span>Model ms</span></div>
        <div><b>{stats.roundTripMs}</b><span>Round trip ms</span></div>
      </div>

      {health && !health.structure_model && (
        <p className="warn-note">Door and stairs model is not installed. Run training/train.py.</p>
      )}

      <h2>Spoken</h2>
      <ul className="log">
        {log.length === 0 && <li className="empty">Nothing spoken yet.</li>}
        {log.map((entry) => (
          <li key={entry.id} className={entry.urgent ? "urgent" : ""}>
            <time>{entry.time}</time>
            <span>{entry.text}</span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
