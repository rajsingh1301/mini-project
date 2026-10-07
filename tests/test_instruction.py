"""Unit tests for Instruction Generator logic.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.instruction import InstructionGenerator
import config


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


if __name__ == "__main__":
    unittest.main()
