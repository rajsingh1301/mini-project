import { useEffect, useRef } from "react";
import { t } from "../lib/i18n.js";

const PAUSE_MS = 1200;        // Between reads, after speech has finished
const SPEECH_POLL_MS = 300;

/** Sends one full-resolution photo to the backend and returns its explanation in `lang`. */
export async function readOnce(capture, lang) {
  const shot = await capture(1920, 0.9, "read");
  if (!shot) return { error: t(lang, "cameraNotReady") };
  const form = new FormData();
  form.append("image", shot.blob, "frame.jpg");
  form.append("lang", lang);
  try {
    const response = await fetch("/api/read", { method: "POST", body: form });
    return await response.json();
  } catch {
    return { error: t(lang, "cannotReachServer") };
  }
}

/**
 * Read mode: keeps reading what the camera points at. Each read waits until the
 * previous explanation has been spoken, so the user hears complete sentences.
 */
export function useSignReader({ active, capture, lang, isSpeaking, onRead }) {
  const handlers = useRef({ onRead, isSpeaking, lang });
  handlers.current = { onRead, isSpeaking, lang };

  useEffect(() => {
    if (!active) return undefined;
    let alive = true;
    let timer = null;

    const loop = async () => {
      if (!alive) return;
      if (handlers.current.isSpeaking()) {
        timer = setTimeout(loop, SPEECH_POLL_MS);
        return;
      }
      const result = await readOnce(capture, handlers.current.lang);
      if (!alive) return;
      handlers.current.onRead(result);
      timer = setTimeout(loop, PAUSE_MS);
    };

    loop();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [active, capture]);
}
