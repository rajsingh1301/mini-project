import { useEffect, useRef } from "react";

const COLORS = { immediate: "#ff3b3b", near: "#ffb000", far: "#33d17a" };

/** Draws zone lines and detection boxes in the coordinates of the sent frame. */
export function Overlay({ frame, detections, showBoxes, tr }) {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !frame) return;
    const { width, height } = frame;
    if (canvas.width !== width) canvas.width = width;
    if (canvas.height !== height) canvas.height = height;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, width, height);

    ctx.strokeStyle = "rgba(255,255,255,.35)";
    ctx.lineWidth = 1;
    ctx.setLineDash([6, 6]);
    for (const r of [0.35, 0.65]) {
      ctx.beginPath();
      ctx.moveTo(width * r, 0);
      ctx.lineTo(width * r, height);
      ctx.stroke();
    }
    ctx.setLineDash([]);
    if (!showBoxes) return;

    const font = Math.max(13, Math.round(width / 40));
    ctx.font = `700 ${font}px system-ui, sans-serif`;
    for (const d of detections) {
      const [x1, y1, x2, y2] = d.bbox;
      const color = COLORS[d.proximity];
      ctx.strokeStyle = color;
      ctx.lineWidth = d.proximity === "immediate" ? 5 : 3;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      const label = `${d.label}${d.stairs_dir ? ` ${tr(d.stairs_dir === "up" ? "stairsUp" : "stairsDown")}` : ""}${d.approaching ? " ▲" : ""} ${Math.round(d.confidence * 100)}%`;
      const w = ctx.measureText(label).width + 12;
      const ly = Math.max(0, y1 - font - 8);
      ctx.fillStyle = color;
      ctx.fillRect(x1, ly, w, font + 8);
      ctx.fillStyle = "#000";
      ctx.fillText(label, x1 + 6, ly + font + 1);
    }
  }, [frame, detections, showBoxes, tr]);

  return <canvas ref={ref} className="overlay" aria-hidden="true" />;
}
