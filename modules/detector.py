"""Object and obstacle detector using YOLO.

Runs the COCO model for general obstacles and, when its weights exist, a
second custom model for doors and stairs. Both return the same detection dicts.
"""

import threading
from typing import List, Dict, Any, Optional

from ultralytics import YOLO
import config


def pick_device() -> str:
    """CUDA GPU, then Apple GPU, then CPU, unless config.DEVICE forces one."""
    if config.DEVICE:
        return config.DEVICE
    import torch
    if torch.cuda.is_available():
        return "0"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class ObstacleDetector:
    def __init__(self, model_name: str = config.MODEL_NAME, conf_thresh: float = config.CONF_THRESHOLD,
                 structure_model=config.STRUCTURE_MODEL,
                 stairs_direction_model=config.STAIRS_DIRECTION_MODEL):
        self.conf_thresh = conf_thresh
        self.device = pick_device()
        self.model = YOLO(model_name)
        # Class names dictionary from model
        self.names = self.model.names
        self.structure = YOLO(str(structure_model)) if structure_model and structure_model.exists() else None
        # Up/down classifier for stairs crops; only useful together with the structure model
        self.stairs_direction = (YOLO(str(stairs_direction_model))
                                 if self.structure is not None and stairs_direction_model
                                 and stairs_direction_model.exists() else None)
        # One model instance is shared by all web clients; predict is not thread-safe
        self._lock = threading.Lock()

    @property
    def has_structure(self) -> bool:
        return self.structure is not None

    def detect(self, frame, include_structure: bool = True) -> List[Dict[str, Any]]:
        """Runs inference on a single frame and extracts detection metadata.

        Returns a list of structured detections:
            {
                'class_name': str,
                'class_id': int,
                'confidence': float,
                'bbox': [x1, y1, x2, y2],
                'center_x': float,
                'center_y': float,
                'area_ratio': float, # Bounding box area / total frame area
                'norm_cx': float,    # Normalized center x [0.0 - 1.0]
                'norm_bottom': float # Normalized bottom edge y [0.0 - 1.0]
            }
        """
        with self._lock:
            detections = self._run(self.model, frame, self.conf_thresh, self.names)
            if include_structure and self.structure is not None:
                detections += self.detect_structure_unlocked(frame)
        return detections

    def detect_structure(self, frame) -> List[Dict[str, Any]]:
        """Doors and stairs only; empty if the custom model is not installed."""
        if self.structure is None:
            return []
        with self._lock:
            return self.detect_structure_unlocked(frame)

    def detect_structure_unlocked(self, frame) -> List[Dict[str, Any]]:
        names = dict(enumerate(config.STRUCTURE_CLASSES))
        min_conf = min(config.STRUCTURE_CONF.values())
        found = self._run(self.structure, frame, min_conf, names)
        found = [d for d in found if d["confidence"] >= config.STRUCTURE_CONF.get(d["class_name"], min_conf)]
        if self.stairs_direction is not None:
            self._classify_stairs(frame, [d for d in found if d["class_name"] == "stairs"])
        return found

    def _classify_stairs(self, frame, stairs: List[Dict[str, Any]]):
        """Adds `stairs_vote` = (label, confidence) to each stairs detection.

        One frame's guess is only a vote; ObjectTracker turns recent votes into
        the `stairs_dir` that gets spoken.
        """
        if not stairs:
            return
        crops = [crop_with_pad(frame, d["bbox"], config.STAIRS_DIRECTION_PAD) for d in stairs]
        results = self.stairs_direction.predict(source=crops, imgsz=config.STAIRS_DIRECTION_IMGSZ,
                                                device=self.device, verbose=False)
        for det, res in zip(stairs, results):
            det["stairs_vote"] = (res.names[int(res.probs.top1)], round(float(res.probs.top1conf), 2))

    def _run(self, model, frame, conf: float, names: Dict[int, str]) -> List[Dict[str, Any]]:
        results = model.predict(
            source=frame,
            conf=conf,
            iou=config.IOU_THRESHOLD,
            device=self.device,
            verbose=False
        )

        detections = []
        h, w = frame.shape[:2]
        total_frame_area = float(w * h)

        if not results or len(results) == 0:
            return detections

        first_res = results[0]
        boxes = first_res.boxes
        if boxes is None or len(boxes) == 0:
            return detections

        for box in boxes:
            xyxy = box.xyxy[0].cpu().numpy()
            conf_val = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())
            cls_name = names.get(cls_id, f"obj_{cls_id}")
            detections.append(make_detection(cls_name, cls_id, conf_val, xyxy, w, h, total_frame_area))

        return detections


def crop_with_pad(frame, bbox: List[int], pad: float):
    """Crop of `bbox` grown by `pad` (fraction of box size) per side, clipped to the frame."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    px, py = int((x2 - x1) * pad), int((y2 - y1) * pad)
    return frame[max(0, y1 - py):min(h, y2 + py), max(0, x1 - px):min(w, x2 + px)]


def make_detection(cls_name: str, cls_id: int, conf: float, xyxy, w: int, h: int,
                   total_frame_area: Optional[float] = None) -> Dict[str, Any]:
    """Builds the detection dict shared by the whole pipeline."""
    x1, y1, x2, y2 = (float(v) for v in xyxy)
    bw = max(0.0, x2 - x1)
    bh = max(0.0, y2 - y1)
    area_ratio = (bw * bh) / (total_frame_area or float(w * h))
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    return {
        "class_name": cls_name,
        "class_id": cls_id,
        "confidence": round(conf, 2),
        "bbox": [int(x1), int(y1), int(x2), int(y2)],
        "center_x": cx,
        "center_y": cy,
        "norm_cx": cx / float(w),
        "norm_bottom": y2 / float(h),
        "area_ratio": area_ratio
    }
