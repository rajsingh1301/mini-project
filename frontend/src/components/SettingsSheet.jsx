import { useEffect, useRef } from "react";

function Toggle({ id, label, hint, checked, onChange }) {
  return (
    <label className="setting" htmlFor={id}>
      <span>
        {label}
        {hint && <small>{hint}</small>}
      </span>
      <input id={id} type="checkbox" role="switch" checked={checked} onChange={(e) => onChange(e.target.checked)} />
    </label>
  );
}

/** Settings dialog. Opened with the small gear button; Escape or Done closes it. */
export function SettingsSheet({ open, settings, update, voices, onClose, onTest }) {
  const ref = useRef(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog ref={ref} className="sheet" onClose={onClose} aria-labelledby="settings-title">
      <h2 id="settings-title">Settings</h2>

      <label className="setting" htmlFor="rate">
        <span>Speech speed <small>{settings.rate.toFixed(1)}x</small></span>
        <input id="rate" type="range" min="0.6" max="1.8" step="0.1" value={settings.rate}
               onChange={(e) => update({ rate: Number(e.target.value) })} />
      </label>

      <label className="setting" htmlFor="voice">
        <span>Voice</span>
        <select id="voice" value={settings.voiceURI} onChange={(e) => update({ voiceURI: e.target.value })}>
          <option value="">Automatic</option>
          {voices.map((v) => <option key={v.voiceURI} value={v.voiceURI}>{v.name} ({v.lang})</option>)}
        </select>
      </label>
      <button type="button" className="btn small" onClick={onTest}>Test voice</button>

      <Toggle id="vibrate" label="Vibrate on warnings" hint="Stop and stairs alerts (Android)"
              checked={settings.vibrate} onChange={(v) => update({ vibrate: v })} />
      <Toggle id="boxes" label="Show boxes" hint="Draw what the camera sees"
              checked={settings.showBoxes} onChange={(v) => update({ showBoxes: v })} />
      <Toggle id="details" label="Show details" hint="Zones, speed and history, for helpers"
              checked={settings.showDetails} onChange={(v) => update({ showDetails: v })} />

      <p className="keys">Keyboard: <kbd>Space</kbd> start or stop, <kbd>R</kbd> read mode,
        <kbd>Enter</kbd> repeat, <kbd>M</kbd> mute</p>

      <button type="button" className="btn primary" onClick={onClose}>Done</button>
    </dialog>
  );
}
