import { useEffect } from "react";

/** Keeps the phone screen on while `active`, so guidance never stops mid-walk. */
export function useWakeLock(active) {
  useEffect(() => {
    if (!active || !("wakeLock" in navigator)) return undefined;
    let lock = null;
    let cancelled = false;
    const acquire = async () => {
      try {
        lock = await navigator.wakeLock.request("screen");
      } catch {
        // Battery saver or unsupported: guidance still works, the screen may sleep
      }
      if (cancelled) lock?.release();
    };
    // The lock is dropped whenever the tab is hidden; take it again on return
    const onVisible = () => document.visibilityState === "visible" && acquire();
    acquire();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", onVisible);
      lock?.release();
    };
  }, [active]);
}
