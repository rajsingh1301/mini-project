import { useDialog } from "../hooks/useDialog.js";
import { LANGUAGES, languageInfo } from "../lib/i18n.js";
import { Icon } from "./Icon.jsx";

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
export function SettingsSheet({ open, settings, update, voices, missingVoice, tr, onClose, onTest }) {
  const ref = useDialog(open);

  return (
    <dialog ref={ref} className="sheet" onClose={onClose} aria-labelledby="settings-title">
      <div className="sheet-header">
        <h2 id="settings-title">{tr("settings")}</h2>
        <button type="button" className="icon-btn" onClick={onClose} aria-label={tr("closeSettings")} autoFocus>
          <Icon name="close" />
        </button>
      </div>

      <div className="sheet-body">
        <label className="setting setting-select" htmlFor="language">
          <span>{tr("language")}</span>
          <select id="language" value={settings.language} onChange={(e) => update({ language: e.target.value, voiceURI: "" })}>
            {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.native}</option>)}
          </select>
        </label>
        {missingVoice && (
          <p className="note" role="status">{tr("noVoice", { language: languageInfo(settings.language).name })}</p>
        )}

        <label className="setting setting-range" htmlFor="rate">
          <span>{tr("speechSpeed")} <small>{tr("speedValue", { rate: settings.rate.toFixed(1) })}</small></span>
          <input id="rate" type="range" min="0.6" max="1.8" step="0.1" value={settings.rate}
                 aria-valuetext={tr("speedValue", { rate: settings.rate.toFixed(1) })}
                 onChange={(e) => update({ rate: Number(e.target.value) })} />
        </label>

        <label className="setting setting-select" htmlFor="voice">
          <span>{tr("voice")}</span>
          <select id="voice" value={settings.voiceURI} onChange={(e) => update({ voiceURI: e.target.value })}>
            <option value="">{tr("automatic")}</option>
            {voices.map((v) => <option key={v.voiceURI} value={v.voiceURI}>{v.name} ({v.lang})</option>)}
          </select>
        </label>
        <button type="button" className="btn small" onClick={onTest}>{tr("testVoice")}</button>

        <Toggle id="vibrate" label={tr("vibrate")} hint={tr("vibrateHint")}
                checked={settings.vibrate} onChange={(v) => update({ vibrate: v })} />
        <Toggle id="boxes" label={tr("showBoxes")} hint={tr("showBoxesHint")}
                checked={settings.showBoxes} onChange={(v) => update({ showBoxes: v })} />
        <Toggle id="details" label={tr("showDetails")} hint={tr("showDetailsHint")}
                checked={settings.showDetails} onChange={(v) => update({ showDetails: v })} />

        <p className="keys">{tr("keyboardShortcuts")}</p>
      </div>

      <div className="sheet-footer"><button type="button" className="btn primary" onClick={onClose}>{tr("done")}</button></div>
    </dialog>
  );
}
