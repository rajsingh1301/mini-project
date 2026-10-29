"""Unit tests for Instruction Generator logic.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.instruction import InstructionGenerator
import config


def det(cls, norm_cx, area_ratio, norm_bottom=0.6, **extra):
    d = {"class_name": cls, "class_id": 0, "confidence": 0.9, "bbox": [0, 0, 10, 10],
         "norm_cx": norm_cx, "area_ratio": area_ratio, "norm_bottom": norm_bottom}
    d.update(extra)
    return d


class TestInstructionGenerator(unittest.TestCase):
    def setUp(self):
        self.engine = InstructionGenerator()

    def test_direction_sectors(self):
        # Center = ahead
        self.assertEqual(self.engine.determine_direction(0.50), "ahead")
        # Left (< 0.35)
        self.assertEqual(self.engine.determine_direction(0.20), "left")
        # Right (> 0.65)
        self.assertEqual(self.engine.determine_direction(0.80), "right")

    def test_proximity_levels(self):
        self.assertEqual(self.engine.determine_proximity(0.25), "immediate")
        self.assertEqual(self.engine.determine_proximity(0.10), "near")
        self.assertEqual(self.engine.determine_proximity(0.01), "far")

    def test_stairs_proximity_uses_box_bottom(self):
        # A staircase can fill half the frame while still far away
        self.assertEqual(self.engine.determine_proximity(0.5, "stairs", 0.60), "far")
        self.assertEqual(self.engine.determine_proximity(0.1, "stairs", 0.80), "near")
        self.assertEqual(self.engine.determine_proximity(0.1, "stairs", 0.95), "immediate")

    def test_hazard_prioritization(self):
        # Two obstacles:
        # 1. A small chair far away on the right
        # 2. A large person immediately ahead
        chair = {
            "class_name": "chair",
            "class_id": 56,
            "confidence": 0.85,
            "bbox": [500, 200, 560, 300],
            "norm_cx": 0.85,
            "area_ratio": 0.02
        }
        person = {
            "class_name": "person",
            "class_id": 0,
            "confidence": 0.90,
            "bbox": [200, 100, 440, 480],
            "norm_cx": 0.50,
            "area_ratio": 0.30
        }

        inst = self.engine.generate_instruction([chair, person])
        # Person directly ahead with large area ratio must trigger immediate Stop warning
        self.assertIsNotNone(inst)
        self.assertIn("Stop", inst)
        self.assertIn("person", inst.lower())

    def test_stairs_ahead_is_an_emergency(self):
        inst = self.engine.generate_instruction([det("stairs", 0.5, 0.3, norm_bottom=0.97)], now=100.0)
        self.assertEqual(inst, "Stop! stairs ahead")

    def test_stairs_outrank_a_nearby_person(self):
        stairs = det("stairs", 0.5, 0.2, norm_bottom=0.8)    # near
        person = det("person", 0.2, 0.09)                    # near, off to the left
        self.assertEqual(self.engine.generate_instruction([person, stairs], now=100.0), "Stairs ahead, slow down")

    def test_stairs_direction_phrases(self):
        build = InstructionGenerator.build_phrase
        self.assertEqual(build("stairs", "ahead", "immediate", stairs_dir="down"), "Stop! stairs going down ahead")
        self.assertEqual(build("stairs", "ahead", "near", stairs_dir="up"), "Stairs going up ahead, slow down")
        self.assertEqual(build("stairs", "left", "near", stairs_dir="down"), "Stairs going down on your left")
        self.assertEqual(build("stairs", "ahead", "near"), "Stairs ahead, slow down")

    def test_stairs_down_outranks_stairs_up(self):
        down = det("stairs", 0.5, 0.2, norm_bottom=0.8, stairs_dir="down")   # near
        up = det("stairs", 0.5, 0.2, norm_bottom=0.8, stairs_dir="up")
        score = lambda d: self.engine.compute_hazard_score(d, "ahead", "near")
        self.assertGreater(score(down), score(up))

    def test_new_stairs_direction_is_announced_without_waiting(self):
        stairs = det("stairs", 0.5, 0.2, norm_bottom=0.8)
        self.assertEqual(self.engine.generate_instruction([stairs], now=100.0), "Stairs ahead, slow down")
        stairs["stairs_dir"] = "down"
        # Within the 4 s same-object throttle, but the direction is new information
        later = 100.0 + config.MIN_GAP_SECONDS
        self.assertEqual(self.engine.generate_instruction([stairs], now=later), "Stairs going down ahead, slow down")

    def test_door_phrases(self):
        self.assertEqual(self.engine.generate_instruction([det("door", 0.2, 0.1)], now=100.0), "Door on your left")
        self.assertEqual(InstructionGenerator.build_phrase("door", "ahead", "immediate"), "Door just ahead")
        self.assertEqual(InstructionGenerator.build_phrase("door", "ahead", "far"), "Door in distance")

    def test_far_side_objects_are_not_announced(self):
        self.assertIsNone(self.engine.generate_instruction([det("chair", 0.9, 0.01)], now=100.0))

    def test_same_object_is_throttled(self):
        chair = det("chair", 0.2, 0.1)
        self.assertIsNotNone(self.engine.generate_instruction([chair], now=100.0))
        self.assertIsNone(self.engine.generate_instruction([chair], now=101.0))
        later = 100.0 + config.AUDIO_THROTTLE_SECONDS + 0.1
        self.assertIsNotNone(self.engine.generate_instruction([chair], now=later))

    def test_global_gap_between_different_objects(self):
        self.assertIsNotNone(self.engine.generate_instruction([det("chair", 0.2, 0.1)], now=100.0))
        self.assertIsNone(self.engine.generate_instruction([det("bench", 0.8, 0.1)], now=100.5))
        # Emergencies ignore the gap
        self.assertIn("Stop", self.engine.generate_instruction([det("person", 0.5, 0.3)], now=100.6))

    def test_unconfirmed_detections_are_ignored(self):
        flicker = det("person", 0.5, 0.3, hits=1)
        self.assertIsNone(self.engine.generate_instruction([flicker], now=100.0))
        flicker["hits"] = config.CONFIRM_HITS
        self.assertIsNotNone(self.engine.generate_instruction([flicker], now=100.1))

    def test_approaching_object(self):
        walker = det("person", 0.8, 0.1, growth_rate=config.APPROACH_RATE * 2)
        self.assertEqual(self.engine.generate_instruction([walker], now=100.0), "Person approaching from your right")
        still = det("person", 0.8, 0.1, growth_rate=0.0)
        self.assertGreater(self.engine.compute_hazard_score(walker, "right", "near"),
                           self.engine.compute_hazard_score(still, "right", "near"))

    def test_path_clear_after_warning(self):
        self.assertIn("Stop", self.engine.generate_instruction([det("person", 0.5, 0.3)], now=100.0))
        self.assertIsNone(self.engine.generate_instruction([], now=101.0))
        clear_at = 100.0 + config.PATH_CLEAR_AFTER_SECONDS + 0.1
        self.assertEqual(self.engine.generate_instruction([], now=clear_at), "Path clear")
        # Said only once
        self.assertIsNone(self.engine.generate_instruction([], now=clear_at + 5))


if __name__ == "__main__":
    unittest.main()
