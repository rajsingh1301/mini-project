"""Unit tests for the detector wrapper, with the YOLO models replaced by fakes.
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from modules import detector as detector_module


class FakeBox:
    def __init__(self, xyxy, conf, cls):
        self.xyxy = torch.tensor([xyxy], dtype=torch.float32)
        self.conf = torch.tensor([conf])
        self.cls = torch.tensor([cls])


class FakeResult:
    def __init__(self, boxes):
        self.boxes = boxes


class FakeProbs:
    def __init__(self, top1, conf):
        self.top1 = top1
        self.top1conf = torch.tensor(conf)


class FakeClassResult:
    names = {0: "down", 1: "up"}

    def __init__(self, crop):
        self.crop_shape = crop.shape
        self.probs = FakeProbs(0, 0.91)


class FakeYOLO:
    """Returns fixed boxes; `boxes_for` maps weights name -> list of FakeBox.
    Weights named in `classifiers` act as the stairs up/down classifier."""
    boxes_for = {}
    classifiers = set()
    crops = []

    def __init__(self, weights):
        self.weights = str(weights)
        self.names = {0: "person", 56: "chair"}
        self.calls = 0

    def predict(self, source, conf=None, **kwargs):
        self.calls += 1
        if self.weights in self.classifiers:
            FakeYOLO.crops = source
            return [FakeClassResult(crop) for crop in source]
        return [FakeResult([b for b in self.boxes_for.get(self.weights, []) if float(b.conf) >= conf])]


class TestDetector(unittest.TestCase):
    def setUp(self):
        self.frame = np.zeros((480, 640, 3), np.uint8)
        patcher = mock.patch.object(detector_module, "YOLO", FakeYOLO)
        patcher.start()
        self.addCleanup(patcher.stop)
        FakeYOLO.boxes_for = {
            config.MODEL_NAME: [FakeBox([160, 0, 480, 480], 0.9, 0), FakeBox([0, 0, 64, 48], 0.3, 56)],
            "door_stairs.pt": [FakeBox([0, 240, 640, 480], 0.8, 1), FakeBox([0, 0, 100, 100], 0.42, 0)],
        }

    def test_detection_fields(self):
        detector = detector_module.ObstacleDetector(structure_model=None)
        dets = detector.detect(self.frame)
        # The 0.3 chair is below CONF_THRESHOLD and must be filtered
        self.assertEqual(len(dets), 1)
        d = dets[0]
        self.assertEqual(d["class_name"], "person")
        self.assertEqual(d["bbox"], [160, 0, 480, 480])
        self.assertAlmostEqual(d["norm_cx"], 0.5)
        self.assertAlmostEqual(d["area_ratio"], 0.5)
        self.assertAlmostEqual(d["norm_bottom"], 1.0)

    def test_structure_model_is_optional(self):
        detector = detector_module.ObstacleDetector(structure_model=Path("/nonexistent/door_stairs.pt"))
        self.assertFalse(detector.has_structure)
        self.assertEqual(detector.detect_structure(self.frame), [])

    def test_structure_classes_and_per_class_threshold(self):
        weights = Path(__file__)  # Any existing file; the fake ignores its content
        FakeYOLO.boxes_for[str(weights)] = FakeYOLO.boxes_for.pop("door_stairs.pt")
        detector = detector_module.ObstacleDetector(structure_model=weights)
        found = detector.detect_structure(self.frame)
        # stairs 0.80 passes; door 0.42 is below STRUCTURE_CONF["door"]
        self.assertEqual([d["class_name"] for d in found], ["stairs"])
        merged = detector.detect(self.frame)
        self.assertEqual(sorted(d["class_name"] for d in merged), ["person", "stairs"])
        only_coco = detector.detect(self.frame, include_structure=False)
        self.assertEqual([d["class_name"] for d in only_coco], ["person"])

    def test_stairs_get_a_direction_vote(self):
        structure = Path(__file__)
        classifier = Path(__file__).parent / "test_tracker.py"  # Any other existing file
        FakeYOLO.boxes_for[str(structure)] = FakeYOLO.boxes_for.pop("door_stairs.pt")
        FakeYOLO.classifiers = {str(classifier)}
        self.addCleanup(setattr, FakeYOLO, "classifiers", set())
        detector = detector_module.ObstacleDetector(structure_model=structure, stairs_direction_model=classifier)
        stairs = detector.detect_structure(self.frame)[0]
        self.assertEqual(stairs["stairs_vote"], ("down", 0.91))
        # Crop of [0, 240, 640, 480] grown by the pad, clipped to the 640x480 frame
        pad = int(240 * config.STAIRS_DIRECTION_PAD)
        self.assertEqual(FakeYOLO.crops[0].shape, (240 + pad, 640, 3))

    def test_direction_classifier_needs_the_structure_model(self):
        detector = detector_module.ObstacleDetector(structure_model=None, stairs_direction_model=Path(__file__))
        self.assertIsNone(detector.stairs_direction)

    def test_empty_frame_result(self):
        FakeYOLO.boxes_for = {}
        detector = detector_module.ObstacleDetector(structure_model=None)
        self.assertEqual(detector.detect(self.frame), [])


if __name__ == "__main__":
    unittest.main()
