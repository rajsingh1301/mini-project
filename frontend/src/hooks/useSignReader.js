import { useEffect, useRef } from "react";

const PAUSE_MS = 1200;        // Between reads, after speech has finished
const SPEECH_POLL_MS = 300;

/** Sends one full-resolution photo to the backend and returns its explanation. */
export async function readOnce(capture) {
  const shot = await capture(1920, 0.9, "read");
  if (!shot) return { error: "Camera is not ready." };
  const form = new FormData();
  form.append("image", shot.blob, "frame.jpg");
  try {
    const response = await fetch("/api/read", { method: "POST", body: form });
    return await response.json();
  } catch {
    return { error: "Cannot reach the server." };
  }
}

/**
 * Read mode: keeps reading what the camera points at. Each read waits until the
 * previous explanation has been spoken, so the user hears complete sentences.
 */
export function useSignReader({ active, capture, isSpeaking, onRead }) {
  const handlers = useRef({ onRead, isSpeaking });
  handlers.current = { onRead, isSpeaking };

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
      const result = await readOnce(capture);
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
