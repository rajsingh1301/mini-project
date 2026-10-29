"""Per-user guidance pipeline: detector -> tracker -> instruction engine.

The detector (heavy models) is shared; each session keeps its own tracking and
speech-throttle state, so the desktop app and every web client behave the same.
"""

import time
from typing import Any, Dict, List, Optional

import config
from modules.detector import ObstacleDetector
from modules.instruction import InstructionGenerator
from modules.tracker import ObjectTracker


class GuidanceSession:
    def __init__(self, detector: ObstacleDetector):
        self.detector = detector
        self.tracker = ObjectTracker()
        self.engine = InstructionGenerator()
        self.frame_index = 0
        self.structure_cache: List[Dict[str, Any]] = []

    def step(self, frame, now: Optional[float] = None) -> Dict[str, Any]:
        """Processes one BGR frame and returns detections plus the phrase to speak (or None)."""
        now = time.time() if now is None else now
        t0 = time.time()

        # Doors and stairs move slowly relative to the walker, so the structure
        # model can run on every Nth frame and its boxes are reused in between.
        run_structure = self.frame_index % max(1, config.STRUCTURE_EVERY_N_FRAMES) == 0
        detections = self.detector.detect(frame, include_structure=False)
        if self.detector.has_structure:
            if run_structure:
                self.structure_cache = self.detector.detect_structure(frame)
                detections += self.structure_cache
            else:
                # Reused boxes must not count as new sightings for the tracker
                detections += [dict(d, reused=True) for d in self.structure_cache]
        self.frame_index += 1

        fresh = [d for d in detections if not d.get("reused")]
        self.tracker.update(fresh, now)
        for d in detections:
            if d.get("reused"):
                # The cached dict kept the track_id it got when it was fresh
                track = self.tracker.tracks.get(d.get("track_id"))
                d["hits"] = track["hits"] if track else 0
                d["growth_rate"] = track["growth_rate"] if track else 0.0
                d["stairs_dir"] = track["stairs_dir"] if track else None

        instruction = self.engine.generate_instruction(detections, now)
        return {
            "detections": detections,
            "instruction": instruction,
            "emergency": bool(instruction and instruction.lower().startswith("stop")),
            "latency_ms": round((time.time() - t0) * 1000, 1),
        }

    def describe(self, det: Dict[str, Any]) -> Dict[str, Any]:
        """JSON-friendly view of one detection for the web client."""
        return {
            "label": det["class_name"],
            "confidence": det["confidence"],
            "bbox": det["bbox"],
            "proximity": self.engine.proximity_of(det),
            "direction": self.engine.determine_direction(det["norm_cx"]),
            "approaching": self.engine.is_approaching(det),
            "stairs_dir": det.get("stairs_dir"),
        }
