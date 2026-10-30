/**
 * The big message area. Speech is handled by the app itself, so this region is
 * not live for screen readers (that would read every message twice).
 */
export function Banner({ kind, arrow, text, sub, lines, label, linesLabel }) {
  return (
    <section className={`banner ${kind}`} aria-label={label}>
      <div className="banner-arrow" aria-hidden="true">{arrow}</div>
      <div className="banner-body">
        <p className="banner-label">{label}</p>
        <p className="banner-text">{text}</p>
        {lines?.length > 0 && (
          <ol className="banner-lines" aria-label={linesLabel}>
            {lines.map((line, i) => <li key={i}>{line}</li>)}
          </ol>
        )}
        {sub && <p className="banner-sub">{sub}</p>}
      </div>
    </section>
  );
}
