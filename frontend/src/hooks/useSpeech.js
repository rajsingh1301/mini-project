import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { languageInfo, t } from "../lib/i18n.js";

const supported = typeof window !== "undefined" && "speechSynthesis" in window;

const inLanguage = (voice, code) => voice.lang?.toLowerCase().replace("_", "-").startsWith(code);

/**
 * Picks the voice the user chose, else the language's Indian voice, else any voice for it.
 * Voices stored on the device come first: online voices stop working without a connection.
 */
function chooseVoice(voices, voiceURI, code) {
  const best = (list) => list.find((v) => v.lang === languageInfo(code).speech) || list[0] || null;
  const forLanguage = voices.filter((v) => inLanguage(v, code));
  return voices.find((v) => v.voiceURI === voiceURI && inLanguage(v, code))
    || best(forLanguage.filter((v) => v.localService))
    || best(forLanguage);
}

/**
 * Browser text-to-speech with the same rules as the desktop TTS queue:
 * urgent phrases interrupt, ordinary ones are dropped while speaking (no backlog).
 *
 * `lang` is the language actually spoken: the chosen one, or English when this device has no
 * voice for it (a Hindi sentence read by an English voice is unintelligible). `missingVoice`
 * tells the settings dialog to explain that.
 */
export function useSpeech(settings) {
  const [allVoices, setAllVoices] = useState([]);
  const lastText = useRef("");
  const lastUrgent = useRef({ text: "", at: 0 });
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  useEffect(() => {
    if (!supported) return undefined;
    const load = () => setAllVoices(window.speechSynthesis.getVoices());
    load();
    window.speechSynthesis.addEventListener("voiceschanged", load);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", load);
  }, []);

  // Voices not loaded yet (some desktop browsers): assume the chosen language works
  const wanted = settings.language;
  const missingVoice = allVoices.length > 0 && wanted !== "en" && !allVoices.some((v) => inLanguage(v, wanted));
  const lang = missingVoice ? "en" : wanted;
  const voices = useMemo(() => allVoices.filter((v) => inLanguage(v, lang)), [allVoices, lang]);

  const voicesRef = useRef(voices);
  voicesRef.current = voices;
  const langRef = useRef(lang);
  langRef.current = lang;

  /**
   * urgent: interrupts current speech (never repeats the same alert within 4 s).
   * force:  interrupts current speech (user asked for it, e.g. Repeat).
   * otherwise: skipped if something is already being spoken.
   */
  const speak = useCallback((text, { urgent = false, force = false } = {}) => {
    if (!text) return;
    lastText.current = text;
    const s = settingsRef.current;
    if (s.muted || !supported) return;
    const synth = window.speechSynthesis;
    const now = performance.now();
    if (urgent) {
      if (text === lastUrgent.current.text && (synth.speaking || now - lastUrgent.current.at < 4000)) return;
      lastUrgent.current = { text, at: now };
      synth.cancel();
    } else if (force) {
      synth.cancel();
    } else if (synth.speaking || synth.pending) {
      return;
    }
    const u = new SpeechSynthesisUtterance(text);
    const voice = chooseVoice(voicesRef.current, s.voiceURI, langRef.current);
    if (voice) u.voice = voice;
    u.lang = voice?.lang || languageInfo(langRef.current).speech;
    u.rate = s.rate;
    synth.speak(u);
  }, []);

  const repeat = useCallback(
    () => speak(lastText.current || t(langRef.current, "nothingToRepeat"), { force: true }), [speak]);
  const cancel = useCallback(() => supported && window.speechSynthesis.cancel(), []);
  const isSpeaking = useCallback(() => supported && (window.speechSynthesis.speaking || window.speechSynthesis.pending), []);

  return { speak, repeat, cancel, isSpeaking, voices, supported, lang, missingVoice };
}
