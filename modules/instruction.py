"""Instruction Generator: Hazard Prioritization and Action Directive Engine.
"""

import time
from typing import List, Dict, Any, Optional
import config


class InstructionGenerator:
    def __init__(self):
        # Cache to throttle speech: key -> last_announced_timestamp
        self.last_announced = {}
        self.last_any_announced = 0.0
        # Keep track of last high-priority directive for HUD display
        self.last_active_directive = "Path clear"

    def determine_direction(self, norm_cx: float) -> str:
        """Determines spatial sector from normalized horizontal center."""
        if norm_cx < config.LEFT_SECTOR_RATIO:
            return "left"
        elif norm_cx > config.RIGHT_SECTOR_RATIO:
            return "right"
        else:
            return "ahead"

    def determine_proximity(self, area_ratio: float) -> str:
        """Estimates proximity level based on relative bounding box scale."""
        if area_ratio >= config.IMMEDIATE_PROXIMITY_THRESHOLD:
            return "immediate"
        elif area_ratio >= config.NEAR_PROXIMITY_THRESHOLD:
            return "near"
        else:
            return "far"

    def compute_hazard_score(self, det: Dict[str, Any], direction: str, proximity: str) -> float:
        """Computes Hazard Risk Index (HRI).
        
        Formula:
          HRI = (area_ratio * 10) + alignment_penalty + class_weight
        """
        area_ratio = det.get("area_ratio", 0.0)
        norm_cx = det.get("norm_cx", 0.5)
        cls_name = det.get("class_name", "")

        # Alignment factor: 1.0 at dead center (norm_cx = 0.5), decaying to 0 at edges
        alignment_score = max(0.0, 1.0 - 2.0 * abs(norm_cx - 0.5))

        # Class severity weight
        class_weight = config.PRIORITY_CLASSES.get(cls_name.lower(), 0.5)

        # Scale proximity impact heavily for large boxes
        proximity_boost = 2.0 if proximity == "immediate" else (1.0 if proximity == "near" else 0.2)

        hazard_score = (area_ratio * 10.0 * proximity_boost) + (alignment_score * 0.8) + (class_weight * 0.5)
        return round(hazard_score, 3)

    def generate_instruction(self, detections: List[Dict[str, Any]]) -> Optional[str]:
        """Evaluates all detections in the frame and returns the highest priority
        action directive, applying chatter-suppression throttling.
        """
        now = time.time()

        if not detections:
            # If path was blocked previously and has been clear for a while
            return None

        # 1. Annotate each detection with direction, proximity and hazard score
        scored_hazards = []
        for det in detections:
            direction = self.determine_direction(det["norm_cx"])
            proximity = self.determine_proximity(det["area_ratio"])
            score = self.compute_hazard_score(det, direction, proximity)

            scored_hazards.append({
                "det": det,
                "direction": direction,
                "proximity": proximity,
                "score": score,
                "class_name": det["class_name"]
            })

        # 2. Sort hazards descending by risk score
        scored_hazards.sort(key=lambda h: h["score"], reverse=True)

        # 3. Find the top candidate that is not throttled
        for candidate in scored_hazards:
            cls = candidate["class_name"]
            direction = candidate["direction"]
            proximity = candidate["proximity"]
            cache_key = f"{cls}_{direction}"

            # Determine throttling window: critical "immediate" alerts have a shorter cooldown
            cooldown = config.CRITICAL_OVERRIDE_SECONDS if proximity == "immediate" else config.AUDIO_THROTTLE_SECONDS

            # Global gap: avoid back-to-back phrases about different objects
            if proximity != "immediate" and (now - self.last_any_announced) < config.MIN_GAP_SECONDS:
                continue

            last_time = self.last_announced.get(cache_key, 0)
            if (now - last_time) >= cooldown:
                # Build concise imperative instruction
                if proximity == "immediate":
                    if direction == "ahead":
                        phrase = f"Stop! {cls} ahead"
                    else:
                        phrase = f"Caution, {cls} on {direction}"
                elif proximity == "near":
                    if direction == "ahead":
                        phrase = f"{cls} ahead"
                    else:
                        phrase = f"{cls} on {direction}"
                else:
                    # 'far' object: only mention if in direct walking path
                    if direction == "ahead":
                        phrase = f"{cls} in distance"
                    else:
                        continue  # Skip far peripheral objects to prevent cognitive clutter

                # Update timestamp and active state
                self.last_announced[cache_key] = now
                self.last_any_announced = now
                self.last_active_directive = phrase
                return phrase

        return None
