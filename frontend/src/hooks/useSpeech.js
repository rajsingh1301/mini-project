import { useCallback, useEffect, useRef, useState } from "react";

const supported = typeof window !== "undefined" && "speechSynthesis" in window;

/** Picks the saved voice, else Indian English, else any English voice. */
function chooseVoice(voices, voiceURI) {
  return voices.find((v) => v.voiceURI === voiceURI)
    || voices.find((v) => v.lang === "en-IN")
    || voices.find((v) => v.lang?.startsWith("en"))
    || null;
}

/**
 * Browser text-to-speech with the same rules as the desktop TTS queue:
 * urgent phrases interrupt, ordinary ones are dropped while speaking (no backlog).
 */
export function useSpeech(settings) {
  const [voices, setVoices] = useState([]);
  const lastText = useRef("");
  const lastUrgent = useRef({ text: "", at: 0 });
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  useEffect(() => {
    if (!supported) return undefined;
    const load = () => setVoices(window.speechSynthesis.getVoices().filter((v) => v.lang?.startsWith("en")));
    load();
    window.speechSynthesis.addEventListener("voiceschanged", load);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", load);
  }, []);

  const voicesRef = useRef(voices);
  voicesRef.current = voices;

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
    const voice = chooseVoice(voicesRef.current, s.voiceURI);
    if (voice) u.voice = voice;
    u.lang = voice?.lang || "en-IN";
    u.rate = s.rate;
    synth.speak(u);
  }, []);

  const repeat = useCallback(() => speak(lastText.current || "Nothing to repeat yet.", { force: true }), [speak]);
  const cancel = useCallback(() => supported && window.speechSynthesis.cancel(), []);
  const isSpeaking = useCallback(() => supported && (window.speechSynthesis.speaking || window.speechSynthesis.pending), []);

  return { speak, repeat, cancel, isSpeaking, voices, supported };
}
