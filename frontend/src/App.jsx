import { useCallback, useEffect, useRef, useState } from "react";
import { Banner } from "./components/Banner.jsx";
import { Details } from "./components/Details.jsx";
import { Overlay } from "./components/Overlay.jsx";
import { SettingsSheet } from "./components/SettingsSheet.jsx";
import { useCamera } from "./hooks/useCamera.js";
import { useGuidanceStream } from "./hooks/useGuidanceStream.js";
import { useSettings } from "./hooks/useSettings.js";
import { useSignReader } from "./hooks/useSignReader.js";
import { useSpeech } from "./hooks/useSpeech.js";
import { useWakeLock } from "./hooks/useWakeLock.js";
import { arrowFor, kindFor, sameText, vibrationFor } from "./lib/guidance.js";

const IDLE_BANNER = { kind: "clear", arrow: "👁", text: "Tap Start", sub: "Hold the phone at chest height, camera facing forward." };
const STATUS_TEXT = { idle: "Off", connecting: "Connecting", live: "Live", lost: "Connection lost", reconnecting: "Reconnecting" };
const HINT_REPEAT_MS = 6000;

export default function App() {
  const [settings, update] = useSettings();
  const speech = useSpeech(settings);
  const camera = useCamera();

  const [phase, setPhase] = useState("idle"); // idle | starting | walk | read
  const [status, setStatus] = useState("idle");
  const [banner, setBanner] = useState(IDLE_BANNER);
  const [frame, setFrame] = useState(null);
  const [detections, setDetections] = useState([]);
  const [stats, setStats] = useState({ fps: 0, modelMs: 0, roundTripMs: 0 });
  const [log, setLog] = useState([]);
  const [health, setHealth] = useState(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [torchOn, setTorchOn] = useState(false);

  const fpsCounter = useRef({ frames: 0, since: 0 });
  const lastRead = useRef({ text: null, kind: null, summary: "" });
  const lastHintAt = useRef(0);
  const forceRead = useRef(false);
  const logId = useRef(0);

  const running = phase === "walk" || phase === "read";
  useWakeLock(running);

  useEffect(() => {
    fetch("/api/health").then((r) => r.json()).then(setHealth).catch(() => setHealth(null));
  }, []);

  const addLog = useCallback((text, urgent = false) => {
    const time = new Date().toLocaleTimeString([], { hour12: false });
    setLog((prev) => [{ id: ++logId.current, text, urgent, time }, ...prev].slice(0, 40));
  }, []);

  const say = useCallback((text, options) => {
    speech.speak(text, options);
    addLog(text, Boolean(options?.urgent));
  }, [speech, addLog]);

  /* ---------- Walk mode ---------- */
  const onResult = useCallback((res, roundTrip) => {
    setFrame({ width: res.width, height: res.height });
    setDetections(res.detections);

    const now = performance.now();
    const c = fpsCounter.current;
    c.frames += 1;
    if (now - c.since >= 1000) {
      setStats({ fps: Math.round((c.frames * 1000) / (now - c.since)), modelMs: Math.round(res.latency_ms),
                 roundTripMs: Math.round(roundTrip) });
      c.frames = 0;
      c.since = now;
    }

    if (res.instruction) {
      const kind = kindFor(res.instruction, res.emergency);
      setBanner({ kind, arrow: arrowFor(res.instruction), text: res.instruction,
                  sub: res.emergency ? "Immediate hazard" : "" });
      say(res.instruction, { urgent: res.emergency });
      const pattern = vibrationFor(res.instruction, res.emergency);
      if (pattern && settings.vibrate && navigator.vibrate) navigator.vibrate(pattern);
    } else if (!res.detections.length) {
      setBanner((b) => (b.kind === "stop" ? b : { kind: "clear", arrow: "✓", text: "Path clear", sub: "" }));
    }
  }, [say, settings.vibrate]);

  const onStatus = useCallback((next) => {
    setStatus(next);
    if (next === "lost") {
      setBanner({ kind: "stop", arrow: "!", text: "Connection lost", sub: "Trying again…" });
      say("Connection lost. Trying again.", { urgent: true });
    } else if (next === "live") {
      setBanner((b) => (b.text === "Connection lost"
        ? { kind: "info", arrow: "↑", text: "Connected again", sub: "" } : b));
    }
  }, [say]);

  useGuidanceStream({ active: phase === "walk", capture: camera.capture, onResult, onStatus });

  /* ---------- Read mode ---------- */
  const onRead = useCallback((res) => {
    const forced = forceRead.current;
    forceRead.current = false;
    const now = performance.now();

    if (res.error) {
      setBanner({ kind: "stop", arrow: "!", text: "Cannot read", sub: res.error });
      if (forced || now - lastHintAt.current > HINT_REPEAT_MS) {
        lastHintAt.current = now;
        say(res.error, { force: true });
      }
      return;
    }

    if (res.text || res.kind) {
      setBanner({ kind: "read", arrow: "Aa", text: res.summary, lines: res.lines, sub: "" });
      const prev = lastRead.current;
      const same = prev.kind === res.kind && sameText(prev.text, res.text)
        && (res.kind !== "traffic_light" || prev.summary === res.summary);
      if (!same || forced) {
        lastRead.current = { text: res.text, kind: res.kind, summary: res.summary };
        say(res.summary, { force: true });
      }
    } else {
      // Nothing readable: forget the last board so pointing back at it reads it again
      lastRead.current = { text: null, kind: null, summary: "" };
      setBanner({ kind: "info", arrow: "Aa", text: "Looking for text…", sub: res.hints?.[0] || "" });
      if (forced || now - lastHintAt.current > HINT_REPEAT_MS) {
        lastHintAt.current = now;
        say(res.summary || "No text found.", { force: forced });
      }
    }
  }, [say]);

  useSignReader({ active: phase === "read", capture: camera.capture, isSpeaking: speech.isSpeaking, onRead });

  /* ---------- Controls ---------- */
  const start = useCallback(async () => {
    if (phase !== "idle") return;
    // Speak inside the tap: iPhones only allow speech that starts from a user gesture
    speech.speak("Starting camera.", { force: true });
    setPhase("starting");
    setBanner({ kind: "info", arrow: "…", text: "Starting camera…", sub: "Allow camera access if asked." });
    try {
      await camera.start();
    } catch (error) {
      setPhase("idle");
      const insecure = !window.isSecureContext;
      const msg = insecure
        ? "Camera needs a secure page. Open the https address shown by run_server.py."
        : "Camera is blocked or missing. Allow camera access, then tap Start again.";
      setBanner({ kind: "stop", arrow: "!", text: "Camera unavailable", sub: msg });
      say(msg, { force: true });
      return;
    }
    fpsCounter.current = { frames: 0, since: performance.now() };
    setPhase("walk");
    setBanner({ kind: "info", arrow: "↑", text: "Walking guidance on", sub: "Point the phone ahead." });
    say("Walking guidance on.", { force: true });
  }, [phase, camera, speech, say]);

  const stop = useCallback(() => {
    camera.stop();
    setPhase("idle");
    setStatus("idle");
    setDetections([]);
    setTorchOn(false);
    setStats({ fps: 0, modelMs: 0, roundTripMs: 0 });
    setBanner(IDLE_BANNER);
    speech.speak("Guidance stopped.", { force: true });
  }, [camera, speech]);

  const toggleRead = useCallback(() => {
    if (phase === "walk") {
      lastRead.current = { text: null, kind: null, summary: "" };
      lastHintAt.current = performance.now();
      setDetections([]);
      setStatus("live");
      setPhase("read");
      setBanner({ kind: "info", arrow: "Aa", text: "Read mode", sub: "Point the phone at the sign or board." });
      say("Read mode. Point the phone at the sign.", { force: true });
    } else if (phase === "read") {
      if (torchOn) camera.setTorch(false);
      setTorchOn(false);
      setPhase("walk");
      setBanner({ kind: "info", arrow: "↑", text: "Walking guidance on", sub: "" });
      say("Walking guidance on.", { force: true });
    }
  }, [phase, camera, torchOn, say]);

  const readAgain = useCallback(() => {
    forceRead.current = true;
    speech.speak("Reading.", { force: true });
  }, [speech]);

  const toggleTorch = useCallback(async () => {
    const ok = await camera.setTorch(!torchOn);
    if (ok) {
      setTorchOn(!torchOn);
      speech.speak(torchOn ? "Light off." : "Light on.", { force: true });
    }
  }, [camera, torchOn, speech]);

  const toggleMute = useCallback(() => {
    if (!settings.muted) speech.cancel();
    update({ muted: !settings.muted });
  }, [settings.muted, update, speech]);

  useEffect(() => {
    const onKey = (e) => {
      if (settingsOpen || e.metaKey || e.ctrlKey || e.altKey) return;
      const tag = e.target.tagName;
      if (tag === "INPUT" || tag === "SELECT") return;
      // Let Space and Enter keep activating a focused button
      if (tag === "BUTTON" && (e.code === "Space" || e.key === "Enter")) return;
      if (e.code === "Space") {
        e.preventDefault();
        running ? stop() : start();
      } else if (e.key === "r" || e.key === "R") toggleRead();
      else if (e.key === "Enter") speech.repeat();
      else if (e.key === "m" || e.key === "M") toggleMute();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [settingsOpen, running, start, stop, toggleRead, toggleMute, speech]);

  return (
    <div className={`app phase-${phase}`}>
      <header className="top">
        <div className="brand">
          <span className="logo" aria-hidden="true">👁</span>
          <h1>Guide Eye</h1>
        </div>
        <span className={`status ${status}`} role="status">
          {phase === "read" ? "Reading" : STATUS_TEXT[status]}
        </span>
        <button type="button" className="icon-btn" onClick={() => setSettingsOpen(true)} aria-label="Settings">⚙</button>
      </header>

      <div className="main">
        <div className="view">
          <div className={`stage ${banner.kind === "stop" ? "alert" : ""}`}>
            <video ref={camera.videoRef} playsInline muted aria-hidden="true" />
            {phase === "walk" && <Overlay frame={frame} detections={detections} showBoxes={settings.showBoxes} />}
            {phase === "idle" && (
              <button type="button" className="start-cover" onClick={start} aria-label="Start guidance">
                <span className="start-icon" aria-hidden="true">▶</span>
                <span className="start-label">Start</span>
                <span className="start-sub">Tap anywhere here</span>
              </button>
            )}
          </div>
          <Banner {...banner} />
        </div>

        {settings.showDetails && (
          <Details detections={detections} stats={stats} log={log} health={health} />
        )}
      </div>

      <nav className="controls" aria-label="Controls">
        {phase === "idle" || phase === "starting" ? (
          <button type="button" className="btn primary huge" onClick={start} disabled={phase === "starting"}>
            {phase === "starting" ? "Starting…" : "Start guidance"}
          </button>
        ) : (
          <>
            <div className="row big">
              <button type="button" className="btn read" onClick={toggleRead}>
                {phase === "read" ? "Back to walking" : "Read sign"}
              </button>
              <button type="button" className="btn danger" onClick={stop}>Stop</button>
            </div>
            <div className="row">
              {phase === "read" && <button type="button" className="btn" onClick={readAgain}>Read again</button>}
              <button type="button" className="btn" onClick={speech.repeat}>Repeat</button>
              {phase === "read" && camera.torchSupported && (
                <button type="button" className="btn" aria-pressed={torchOn} onClick={toggleTorch}>Light</button>
              )}
              <button type="button" className="btn" aria-pressed={settings.muted} onClick={toggleMute}>
                {settings.muted ? "Unmute" : "Mute"}
              </button>
            </div>
          </>
        )}
      </nav>

      <SettingsSheet
        open={settingsOpen}
        settings={settings}
        update={update}
        voices={speech.voices}
        onClose={() => setSettingsOpen(false)}
        onTest={() => speech.speak("Stop! stairs ahead.", { force: true })}
      />
    </div>
  );
}
