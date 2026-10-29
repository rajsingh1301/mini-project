"""Unit tests for the frame-to-frame tracker.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from modules.tracker import ObjectTracker, iou


def box_det(cls, bbox, frame_area=640 * 480):
    x1, y1, x2, y2 = bbox
    return {"class_name": cls, "bbox": bbox, "area_ratio": (x2 - x1) * (y2 - y1) / frame_area}


class TestTracker(unittest.TestCase):
    def test_iou(self):
        self.assertAlmostEqual(iou([0, 0, 10, 10], [0, 0, 10, 10]), 1.0)
        self.assertAlmostEqual(iou([0, 0, 10, 10], [20, 20, 30, 30]), 0.0)
        self.assertAlmostEqual(iou([0, 0, 10, 10], [5, 0, 15, 10]), 50 / 150)

    def test_same_object_keeps_its_id_and_counts_hits(self):
        tracker = ObjectTracker()
        a = tracker.update([box_det("person", [100, 100, 200, 300])], now=0.0)[0]
        b = tracker.update([box_det("person", [105, 100, 205, 305])], now=0.1)[0]
        self.assertEqual(a["track_id"], b["track_id"])
        self.assertEqual(a["hits"], 1)
        self.assertEqual(b["hits"], 2)

    def test_different_class_is_a_new_track(self):
        tracker = ObjectTracker()
        a = tracker.update([box_det("person", [100, 100, 200, 300])], now=0.0)[0]
        b = tracker.update([box_det("chair", [100, 100, 200, 300])], now=0.1)[0]
        self.assertNotEqual(a["track_id"], b["track_id"])

    def test_growing_box_has_positive_growth_rate(self):
        tracker = ObjectTracker()
        t = 0.0
        size = 100
        for _ in range(6):
            d = tracker.update([box_det("person", [300 - size // 2, 100, 300 + size // 2, 100 + 2 * size])], now=t)[0]
            t += 0.1
            size += 20
        self.assertGreater(d["growth_rate"], config.APPROACH_RATE)

    def test_still_object_has_no_growth(self):
        tracker = ObjectTracker()
        for i in range(5):
            d = tracker.update([box_det("chair", [100, 100, 200, 200])], now=i * 0.1)[0]
        self.assertAlmostEqual(d["growth_rate"], 0.0)

    def test_old_tracks_expire(self):
        tracker = ObjectTracker()
        a = tracker.update([box_det("person", [100, 100, 200, 300])], now=0.0)[0]
        b = tracker.update([box_det("person", [100, 100, 200, 300])],
                           now=config.TRACK_MAX_AGE_SECONDS + 0.5)[0]
        self.assertNotEqual(a["track_id"], b["track_id"])
        self.assertEqual(b["hits"], 1)


if __name__ == "__main__":
    unittest.main()
