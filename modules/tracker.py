"""Lightweight frame-to-frame tracker.

Matches detections of the same class across frames by box overlap, so the
instruction engine can (1) ignore one-frame flickers and (2) tell whether an
object is getting closer from how fast its box grows: d(area)/dt.
"""

import itertools
from typing import Any, Dict, List, Optional

import config


def iou(a: List[int], b: List[int]) -> float:
    """Intersection-over-union of two [x1, y1, x2, y2] boxes."""
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


class ObjectTracker:
    def __init__(self):
        self.tracks: Dict[int, Dict[str, Any]] = {}
        self._ids = itertools.count(1)

    def update(self, detections: List[Dict[str, Any]], now: float) -> List[Dict[str, Any]]:
        """Adds track_id, hits and growth_rate to each detection (in place) and returns them."""
        # Drop tracks that have not been seen recently
        self.tracks = {tid: t for tid, t in self.tracks.items()
                       if now - t["last_seen"] <= config.TRACK_MAX_AGE_SECONDS}

        # Greedy matching: best-overlapping pairs first
        pairs = []
        for di, det in enumerate(detections):
            for tid, track in self.tracks.items():
                if track["class_name"] == det["class_name"]:
                    overlap = iou(det["bbox"], track["bbox"])
                    if overlap >= config.TRACK_MATCH_IOU:
                        pairs.append((overlap, di, tid))
        pairs.sort(reverse=True)

        matched: Dict[int, int] = {}
        used_tracks = set()
        for _, di, tid in pairs:
            if di not in matched and tid not in used_tracks:
                matched[di] = tid
                used_tracks.add(tid)

        for di, det in enumerate(detections):
            tid: Optional[int] = matched.get(di)
            if tid is None:
                tid = next(self._ids)
                self.tracks[tid] = {"class_name": det["class_name"], "hits": 0,
                                    "growth_rate": 0.0, "area": det["area_ratio"], "last_seen": now}
            track = self.tracks[tid]
            dt = now - track["last_seen"]
            if track["hits"] > 0 and dt > 0:
                rate = (det["area_ratio"] - track["area"]) / dt
                a = config.APPROACH_SMOOTHING
                track["growth_rate"] = a * rate + (1 - a) * track["growth_rate"]
            track.update(bbox=det["bbox"], area=det["area_ratio"], last_seen=now, hits=track["hits"] + 1)

            det["track_id"] = tid
            det["hits"] = track["hits"]
            det["growth_rate"] = round(track["growth_rate"], 4)
        return detections

    def reset(self):
        self.tracks.clear()
