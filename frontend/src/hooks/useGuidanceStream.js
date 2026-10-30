import { useEffect, useRef } from "react";

function socketUrl(lang) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}/ws?lang=${encodeURIComponent(lang)}`;
}

/**
 * Walk mode: sends one small JPEG, waits for the reply, then sends the next.
 * Frames never queue up, so instructions always describe the current view.
 * Reconnects by itself if the connection drops, and when the spoken language changes
 * (the server words each instruction in the language it was connected with).
 */
export function useGuidanceStream({ active, capture, lang, onResult, onStatus }) {
  const handlers = useRef({ onResult, onStatus });
  handlers.current = { onResult, onStatus };

  useEffect(() => {
    if (!active) return undefined;
    let ws = null;
    let alive = true;
    let busy = false;
    let retries = 0;
    let retryTimer = null;
    let sentAt = 0;

    const send = async () => {
      if (!alive || busy || !ws || ws.readyState !== WebSocket.OPEN) return;
      busy = true;
      const shot = await capture(640, 0.7, "walk");
      if (!alive || !ws || ws.readyState !== WebSocket.OPEN) return;
      if (!shot) {
        // Camera not producing frames yet
        busy = false;
        setTimeout(send, 100);
        return;
      }
      sentAt = performance.now();
      ws.send(shot.blob);
    };

    const connect = () => {
      handlers.current.onStatus(retries ? "reconnecting" : "connecting");
      ws = new WebSocket(socketUrl(lang));
      ws.onopen = () => {
        retries = 0;
        busy = false;
        handlers.current.onStatus("live");
        send();
      };
      ws.onmessage = (event) => {
        busy = false;
        const result = JSON.parse(event.data);
        if (!result.error) handlers.current.onResult(result, performance.now() - sentAt);
        send();
      };
      ws.onclose = () => {
        if (!alive) return;
        retries += 1;
        handlers.current.onStatus(retries === 1 ? "lost" : "reconnecting");
        retryTimer = setTimeout(connect, Math.min(4000, 500 * retries));
      };
    };

    connect();
    return () => {
      alive = false;
      clearTimeout(retryTimer);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [active, capture, lang]);
}
