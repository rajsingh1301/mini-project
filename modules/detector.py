"""Object and obstacle detector using YOLOv8.
"""

from typing import List, Dict, Any
from ultralytics import YOLO
import config


class ObstacleDetector:
    def __init__(self, model_name: str = config.MODEL_NAME, conf_thresh: float = config.CONF_THRESHOLD):
        self.conf_thresh = conf_thresh
        self.model = YOLO(model_name)
        # Class names dictionary from model
        self.names = self.model.names

    def detect(self, frame) -> List[Dict[str, Any]]:
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
                'norm_cx': float     # Normalized center x [0.0 - 1.0]
            }
        """
        results = self.model.predict(
            source=frame,
            conf=self.conf_thresh,
            iou=config.IOU_THRESHOLD,
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
            conf = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())
            cls_name = self.names.get(cls_id, f"obj_{cls_id}")

            x1, y1, x2, y2 = xyxy
            bw = max(0.0, x2 - x1)
            bh = max(0.0, y2 - y1)
            box_area = bw * bh
            area_ratio = box_area / total_frame_area

            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            norm_cx = cx / float(w)

            detections.append({
                "class_name": cls_name,
                "class_id": cls_id,
                "confidence": round(conf, 2),
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                "center_x": cx,
                "center_y": cy,
                "norm_cx": norm_cx,
                "area_ratio": area_ratio
            })

        return detections
