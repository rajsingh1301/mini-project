// Pure helpers shared by the UI. No React or browser APIs, so `npm test` can run them in Node.

const RANK = { far: 1, near: 2, immediate: 3 };

/** Words of a text, lower-cased, without punctuation. */
function words(text) {
  return new Set((text || "").toLowerCase().match(/[\p{L}\p{N}]+/gu) || []);
}

/** True when two OCR reads are basically the same board (word overlap >= 60%). */
export function sameText(a, b) {
  const wa = words(a), wb = words(b);
  if (!wa.size && !wb.size) return true;
  if (!wa.size || !wb.size) return false;
  let shared = 0;
  for (const w of wa) if (wb.has(w)) shared++;
  return shared / (wa.size + wb.size - shared) >= 0.6;
}

/** Arrow glyph for the server's `direction` (left, ahead, right) of a spoken instruction. */
export function arrowFor(direction, clear = false) {
  if (clear) return "✓";
  if (direction === "left") return "←";
  if (direction === "right") return "→";
  return "↑";
}

/** Banner style for an instruction: stop (emergency), clear (path clear) or info. */
export function kindFor(emergency, clear = false) {
  if (emergency) return "stop";
  return clear ? "clear" : "info";
}

/** Most urgent object per zone, for the left / ahead / right strip. */
export function zoneSummary(detections) {
  const zones = { left: null, ahead: null, right: null };
  for (const d of detections || []) {
    const best = zones[d.direction];
    if (!best || RANK[d.proximity] > RANK[best.proximity] ||
        (RANK[d.proximity] === RANK[best.proximity] && d.confidence > best.confidence)) {
      zones[d.direction] = d;
    }
  }
  return zones;
}

/** Vibration pattern for the server's alert level ("stop", "caution" or none), or null for none. */
export function vibrationFor(alert) {
  if (alert === "stop") return [300, 100, 300];
  if (alert === "caution") return [120, 80, 120];
  return null;
}

/** Image size that keeps the aspect ratio with the longest side at most maxSide. */
export function fitSize(width, height, maxSide) {
  const scale = Math.min(1, maxSide / Math.max(width, height));
  return { width: Math.round(width * scale), height: Math.round(height * scale) };
}
