import { useCallback, useState } from "react";

const KEY = "guide-eye-settings";
const DEFAULTS = {
  rate: 1.1,          // Speech speed
  voiceURI: "",       // Empty = automatic (Indian English if available)
  vibrate: true,      // Vibrate on Stop and stairs warnings
  muted: false,
  showBoxes: true,    // Draw detections over the camera picture
  showDetails: typeof window !== "undefined" && window.innerWidth >= 900, // FPS, zones, log for helpers
};

function load() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) || "{}") };
  } catch {
    return { ...DEFAULTS };
  }
}

/** User preferences, remembered on this device. */
export function useSettings() {
  const [settings, setSettings] = useState(load);
  const update = useCallback((patch) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      try {
        localStorage.setItem(KEY, JSON.stringify(next));
      } catch {
        // Private mode or blocked storage: settings just last for this visit
      }
      return next;
    });
  }, []);
  return [settings, update];
}
