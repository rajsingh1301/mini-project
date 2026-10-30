import { zoneSummary } from "../lib/guidance.js";

/** Helper and demo view: zones, speed numbers and the spoken history. */
export function Details({ detections, stats, log, health, tr }) {
  const zones = zoneSummary(detections);
  return (
    <aside className="details" aria-label={tr("details")}>
      <div className="zones">
        {["left", "ahead", "right"].map((zone) => {
          const d = zones[zone];
          return (
            <div key={zone} className={`zone ${d ? d.proximity : ""}`}>
              <small>{tr(zone)}</small>
              <b>{d ? d.label : tr("zoneClear")}</b>
              {d?.stairs_dir && <span>{tr(d.stairs_dir === "up" ? "stairsUp" : "stairsDown")}</span>}
              {d?.approaching && <span>{tr("approaching")}</span>}
            </div>
          );
        })}
      </div>

      <div className="stats">
        <div><b>{stats.fps}</b><span>{tr("framesPerSecond")}</span></div>
        <div><b>{stats.modelMs}</b><span>{tr("modelMs")}</span></div>
        <div><b>{stats.roundTripMs}</b><span>{tr("roundTripMs")}</span></div>
      </div>

      {health && !health.structure_model && (
        <p className="warn-note">{tr("structureUnavailable")}</p>
      )}

      <h2>{tr("spokenHistory")}</h2>
      <ul className="log">
        {log.length === 0 && <li className="empty">{tr("nothingSpoken")}</li>}
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
