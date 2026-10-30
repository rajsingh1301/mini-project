"""Instruction Generator: Hazard Prioritization and Action Directive Engine.
"""

import time
from typing import List, Dict, Any, Optional
import config
from modules import phrases


class InstructionGenerator:
    def __init__(self, lang: str = phrases.DEFAULT_LANGUAGE):
        self.lang = phrases.normalize(lang)
        # Direction, alert level and "clear" flag of the last returned phrase (None if none)
        self.last_meta: Optional[Dict[str, Any]] = None
        # Cache to throttle speech: key -> last_announced_timestamp
        self.last_announced = {}
        self.last_any_announced = 0.0
        # Keep track of last high-priority directive for HUD display
        self.last_active_directive = phrases.path_clear(self.lang)
        # "Path clear" is said once after a warning about something ahead
        self.awaiting_clear = False
        self.last_ahead_hazard = 0.0

    def determine_direction(self, norm_cx: float) -> str:
        """Determines spatial sector from normalized horizontal center."""
        if norm_cx < config.LEFT_SECTOR_RATIO:
            return "left"
        elif norm_cx > config.RIGHT_SECTOR_RATIO:
            return "right"
        else:
            return "ahead"

    def determine_proximity(self, area_ratio: float, class_name: str = "",
                            norm_bottom: Optional[float] = None) -> str:
        """Estimates proximity level based on relative bounding box scale.

        Floor-level classes (stairs) use how low the box reaches instead, because a
        staircase fills a large area even when it is still far away.
        """
        if class_name in config.FLOOR_CLASSES and norm_bottom is not None:
            if norm_bottom >= config.FLOOR_IMMEDIATE_BOTTOM:
                return "immediate"
            if norm_bottom >= config.FLOOR_NEAR_BOTTOM:
                return "near"
            return "far"
        if area_ratio >= config.IMMEDIATE_PROXIMITY_THRESHOLD:
            return "immediate"
        elif area_ratio >= config.NEAR_PROXIMITY_THRESHOLD:
            return "near"
        else:
            return "far"

    def proximity_of(self, det: Dict[str, Any]) -> str:
        return self.determine_proximity(det["area_ratio"], det["class_name"], det.get("norm_bottom"))

    @staticmethod
    def is_approaching(det: Dict[str, Any]) -> bool:
        return det.get("growth_rate", 0.0) >= config.APPROACH_RATE

    def compute_hazard_score(self, det: Dict[str, Any], direction: str, proximity: str) -> float:
        """Computes Hazard Risk Index (HRI).

        Formula:
          HRI = area_ratio * 10 * proximity_boost + alignment * 0.8 + class_weight * 0.5
                + approach * 0.3, where approach = min(growth_rate / APPROACH_RATE, 2) when growing
        """
        area_ratio = det.get("area_ratio", 0.0)
        norm_cx = det.get("norm_cx", 0.5)
        cls_name = det.get("class_name", "")

        # Alignment factor: 1.0 at dead center (norm_cx = 0.5), decaying to 0 at edges
        alignment_score = max(0.0, 1.0 - 2.0 * abs(norm_cx - 0.5))

        # Class severity weight
        class_weight = config.PRIORITY_CLASSES.get(cls_name.lower(), 0.5)
        if cls_name == "stairs" and det.get("stairs_dir") == "down":
            class_weight = config.STAIRS_DOWN_WEIGHT

        # Scale proximity impact heavily for large boxes
        proximity_boost = 2.0 if proximity == "immediate" else (1.0 if proximity == "near" else 0.2)
        if cls_name in config.FLOOR_CLASSES:
            # Area is not a distance cue for floor hazards; rank them by proximity level
            area_ratio = {"immediate": 0.3, "near": 0.12, "far": 0.03}[proximity]

        # Objects moving towards the user rank higher
        approach = min(max(det.get("growth_rate", 0.0), 0.0) / config.APPROACH_RATE, 2.0)

        hazard_score = (area_ratio * 10.0 * proximity_boost) + (alignment_score * 0.8) \
            + (class_weight * 0.5) + (approach * 0.3)
        return round(hazard_score, 3)

    @staticmethod
    def build_phrase(cls: str, direction: str, proximity: str, approaching: bool = False,
                     stairs_dir: Optional[str] = None, lang: str = phrases.DEFAULT_LANGUAGE,
                     clearer: Optional[str] = None) -> Optional[str]:
        """Short imperative phrase, or None when the object is not worth announcing."""
        return phrases.instruction(lang, cls, direction, proximity, approaching, stairs_dir, clearer)

    @staticmethod
    def blocked_path(scored: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Summary candidate when several obstacles block the way ahead, else None.

        Doors and stairs are not "blockers" (they have their own phrases). The side
        that looks clearer is only named when exactly one side has nothing close:
        it means "nothing detected there", not a guarantee, so the phrase says "looks".
        """
        def close(h):
            return h["proximity"] in ("near", "immediate") and h["class_name"] != "door"

        blockers = [h for h in scored if close(h) and h["direction"] == "ahead"
                    and h["class_name"] not in config.FLOOR_CLASSES]
        if len(blockers) < config.BLOCKED_MIN_OBJECTS:
            return None
        busy = {h["direction"] for h in scored if close(h)}
        free = [side for side in ("left", "right") if side not in busy]
        return {
            "det": blockers[0]["det"], "direction": "ahead", "class_name": "obstacles",
            "proximity": "immediate" if any(h["proximity"] == "immediate" for h in blockers) else "near",
            "score": max(h["score"] for h in blockers) + 0.01,
            "clearer": free[0] if len(free) == 1 else None,
            "members": blockers,
        }

    @staticmethod
    def alert_level(cls: str, direction: str, proximity: str) -> Optional[str]:
        """Language-independent urgency: "stop" (emergency), "caution" or None.

        Stop = something immediate straight ahead (doors never count). Caution =
        an immediate hazard to the side, or any stairs.
        """
        if cls != "door" and proximity == "immediate" and direction == "ahead":
            return "stop"
        if cls in ("stairs", "obstacles") or (cls != "door" and proximity == "immediate"):
            return "caution"
        return None

    def generate_instruction(self, detections: List[Dict[str, Any]], now: Optional[float] = None) -> Optional[str]:
        """Evaluates all detections in the frame and returns the highest priority
        action directive, applying chatter-suppression throttling.

        Detections that went through ObjectTracker carry `hits`; ones seen in fewer
        than CONFIRM_HITS frames are ignored as possible flicker.
        """
        now = time.time() if now is None else now
        self.last_meta = None
        confirmed = [d for d in detections if d.get("hits", config.CONFIRM_HITS) >= config.CONFIRM_HITS]

        # 1. Annotate each detection with direction, proximity and hazard score
        scored_hazards = []
        for det in confirmed:
            direction = self.determine_direction(det["norm_cx"])
            proximity = self.proximity_of(det)
            score = self.compute_hazard_score(det, direction, proximity)
            if direction == "ahead" and proximity != "far" and det["class_name"] != "door":
                self.last_ahead_hazard = now

            scored_hazards.append({
                "det": det,
                "direction": direction,
                "proximity": proximity,
                "score": score,
                "class_name": det["class_name"]
            })

        # 2. Several obstacles in the way become one summary; sort descending by risk score
        blocked = self.blocked_path(scored_hazards)
        if blocked:
            scored_hazards = [h for h in scored_hazards if h not in blocked["members"]] + [blocked]
        scored_hazards.sort(key=lambda h: h["score"], reverse=True)

        # 3. Find the top candidate that is not throttled
        for candidate in scored_hazards:
            cls = candidate["class_name"]
            direction = candidate["direction"]
            proximity = candidate["proximity"]
            stairs_dir = candidate["det"].get("stairs_dir")
            # A newly learned stairs direction is worth saying even right after "Stairs ahead"
            clearer = candidate.get("clearer")
            cache_key = f"{cls}_{stairs_dir or clearer}_{direction}" if (stairs_dir or clearer) else f"{cls}_{direction}"

            # Determine throttling window: critical alerts and distant objects have their own cooldown
            cooldown = {"immediate": config.CRITICAL_OVERRIDE_SECONDS,
                        "far": config.FAR_THROTTLE_SECONDS}.get(proximity, config.AUDIO_THROTTLE_SECONDS)

            # Global gap: avoid back-to-back phrases about different objects
            if proximity != "immediate" and (now - self.last_any_announced) < config.MIN_GAP_SECONDS:
                continue

            last_time = self.last_announced.get(cache_key, 0)
            if (now - last_time) >= cooldown:
                phrase = self.build_phrase(cls, direction, proximity, self.is_approaching(candidate["det"]),
                                           stairs_dir, self.lang, clearer)
                if phrase is None:
                    continue

                # Update timestamp and active state
                self.last_announced[cache_key] = now
                self.last_any_announced = now
                self.last_active_directive = phrase
                self.last_meta = {"direction": direction, "alert": self.alert_level(cls, direction, proximity),
                                  "clear": False}
                if direction == "ahead" and proximity != "far" and cls != "door":
                    self.awaiting_clear = True
                return phrase

        # 4. Reassure the user once the way ahead has been clear for a while
        if (self.awaiting_clear
                and now - self.last_ahead_hazard >= config.PATH_CLEAR_AFTER_SECONDS
                and now - self.last_any_announced >= config.MIN_GAP_SECONDS):
            self.awaiting_clear = False
            self.last_any_announced = now
            self.last_active_directive = phrases.path_clear(self.lang)
            self.last_meta = {"direction": None, "alert": None, "clear": True}
            return self.last_active_directive

        return None
