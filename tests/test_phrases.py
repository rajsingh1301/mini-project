"""Unit tests for the spoken phrase tables: every language is complete and reads naturally.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from modules import phrases
from modules.instruction import InstructionGenerator
from modules.sign_interpreter import SIGN_RULES, SignInterpreter

COCO_CLASSES = list(config.PRIORITY_CLASSES)


def keys(tree, prefix=""):
    """All leaf paths of a nested dict, so two languages can be compared."""
    if not isinstance(tree, dict):
        return {prefix}
    return {k for name, sub in tree.items() for k in keys(sub, f"{prefix}/{name}")}


class TestTables(unittest.TestCase):
    def test_every_language_has_every_phrase(self):
        for lang in phrases.LANGUAGES:
            with self.subTest(lang=lang):
                self.assertEqual(keys(phrases.TEXT[lang]), keys(phrases.TEXT["en"]))
                self.assertEqual(keys(phrases.READ[lang]), keys(phrases.READ["en"]))

    def test_templates_only_use_known_placeholders(self):
        # Word order differs per language, so the sets may differ, but every
        # placeholder must be one the code fills in (a typo would raise KeyError at runtime)
        import re
        known = {"obj", "where", "from_", "come", "color", "advice", "text", "label", "directions"}
        for table in (phrases.TEXT, phrases.READ):
            for lang in phrases.LANGUAGES:
                for key, template in table[lang].items():
                    if isinstance(template, str):
                        self.assertLessEqual(set(re.findall(r"{(\w+)}", template)), known, (lang, key))

    def test_every_sign_kind_is_translated(self):
        for lang in phrases.SIGN_TEXT:
            self.assertEqual({k for k, *_ in SIGN_RULES}, set(phrases.SIGN_TEXT[lang]), lang)

    def test_announced_classes_have_hindi_names(self):
        for cls in COCO_CLASSES:
            self.assertIn(cls, phrases.HINDI_OBJECTS, cls)

    def test_normalize(self):
        self.assertEqual(phrases.normalize("hi-IN"), "hi")
        self.assertEqual(phrases.normalize("HI"), "hi")
        self.assertEqual(phrases.normalize("fr"), "en")
        self.assertEqual(phrases.normalize(None), "en")


class TestInstructions(unittest.TestCase):
    def test_english_is_unchanged(self):
        build = InstructionGenerator.build_phrase
        self.assertEqual(build("person", "ahead", "immediate"), "Stop! person ahead")
        self.assertEqual(build("chair", "left", "near"), "Chair on your left")
        self.assertEqual(build("car", "right", "far"), None)
        self.assertEqual(build("dog", "left", "near", approaching=True), "Dog approaching from your left")

    def test_hindi_phrases(self):
        build = lambda *a, **k: InstructionGenerator.build_phrase(*a, lang="hi", **k)
        self.assertEqual(build("person", "ahead", "immediate"), "रुकिए! सामने व्यक्ति")
        self.assertEqual(build("car", "left", "immediate"), "सावधान, बाईं ओर कार")
        self.assertEqual(build("chair", "right", "near"), "दाईं ओर कुर्सी")
        self.assertEqual(build("chair", "ahead", "far"), "दूर कुर्सी")
        self.assertIsNone(build("chair", "left", "far"))
        self.assertEqual(build("door", "ahead", "immediate"), "दरवाज़ा बिल्कुल सामने")
        self.assertEqual(build("door", "left", "near"), "बाईं ओर दरवाज़ा")

    def test_hindi_verb_agrees_with_gender(self):
        build = lambda cls, d: InstructionGenerator.build_phrase(cls, d, "near", approaching=True, lang="hi")
        self.assertEqual(build("person", "ahead"), "सामने से व्यक्ति पास आ रहा है")
        self.assertEqual(build("car", "left"), "बाईं ओर से कार पास आ रही है")

    def test_hindi_stairs_direction(self):
        build = lambda proximity, d, direction=None: InstructionGenerator.build_phrase(
            "stairs", d, proximity, stairs_dir=direction, lang="hi")
        self.assertEqual(build("immediate", "ahead", "down"), "रुकिए! सामने नीचे जाती सीढ़ियाँ")
        self.assertEqual(build("near", "ahead", "up"), "सामने ऊपर जाती सीढ़ियाँ, धीरे चलिए")
        self.assertEqual(build("near", "left"), "बाईं ओर सीढ़ियाँ")

    def test_unknown_class_falls_back_to_its_english_name(self):
        self.assertEqual(InstructionGenerator.build_phrase("flux capacitor", "left", "near", lang="hi"),
                         "बाईं ओर flux capacitor")

    def test_engine_speaks_hindi_and_reports_metadata(self):
        engine = InstructionGenerator("hi")
        det = {"class_name": "person", "class_id": 0, "confidence": 0.9, "bbox": [0, 0, 10, 10],
               "norm_cx": 0.5, "area_ratio": 0.3, "norm_bottom": 0.9}
        self.assertEqual(engine.generate_instruction([det], now=100.0), "रुकिए! सामने व्यक्ति")
        self.assertEqual(engine.last_meta, {"direction": "ahead", "alert": "stop", "clear": False})
        # Quiet frame long after: "path clear" in Hindi, flagged as clear
        self.assertEqual(engine.generate_instruction([], now=110.0), "रास्ता साफ़ है")
        self.assertEqual(engine.last_meta, {"direction": None, "alert": None, "clear": True})
        # Nothing to say: no metadata left over from before
        self.assertIsNone(engine.generate_instruction([], now=111.0))
        self.assertIsNone(engine.last_meta)

    def test_alert_levels(self):
        level = InstructionGenerator.alert_level
        self.assertEqual(level("person", "ahead", "immediate"), "stop")
        self.assertEqual(level("stairs", "ahead", "immediate"), "stop")
        self.assertEqual(level("car", "left", "immediate"), "caution")
        self.assertEqual(level("stairs", "ahead", "near"), "caution")
        self.assertIsNone(level("door", "ahead", "immediate"))
        self.assertIsNone(level("chair", "left", "near"))


class TestSigns(unittest.TestCase):
    def setUp(self):
        self.signs = SignInterpreter()

    def test_hindi_boards_are_recognised(self):
        cases = {"निकास": "exit", "आपातकालीन निकास": "exit", "सीढ़ियाँ": "stairs", "शौचालय": "restroom",
                 "ख़तरा": "warning", "धक्का दें": "push", "खींचें": "pull", "प्रवेश निषेध": "no_entry",
                 "प्रवेश": "entrance", "प्लेटफ़ॉर्म नंबर 3": "platform", "बंद है": "closed"}
        for text, kind in cases.items():
            with self.subTest(text=text):
                self.assertEqual(self.signs.classify(text)["kind"], kind)
        self.assertIsNone(self.signs.classify("कमरा नंबर 204"))

    def test_nukta_spelling_variants_match(self):
        # Precomposed (U+095D) and decomposed (U+0922 U+093C) forms of the same letter
        self.assertEqual(self.signs.classify("सी\u095dी")["kind"], "stairs")
        self.assertEqual(self.signs.classify("सी\u0922\u093cी")["kind"], "stairs")

    def test_hindi_explanation(self):
        out = self.signs.explain({"text": "EXIT", "lines": [], "hints": []}, lang="hi")
        self.assertEqual(out["summary"], "निकास का संकेत। इस पर लिखा है: EXIT। यह बाहर जाने का रास्ता दिखाता है।")

    def test_hindi_board_in_english_app(self):
        out = self.signs.explain({"text": "निकास", "lines": [], "hints": []})
        self.assertEqual(out["summary"], "Exit sign. It says: निकास. It shows the way out.")

    def test_hints_follow_the_language(self):
        ocr = {"text": "", "lines": [], "hints": ["It is too dark. Find more light."],
               "hint_codes": [("dark", [])]}
        self.assertEqual(self.signs.explain(ocr)["summary"], "No text found. It is too dark. Find more light.")
        self.assertEqual(self.signs.explain(ocr, lang="hi")["summary"],
                         "कोई लिखावट नहीं मिली। बहुत अँधेरा है। रोशनी वाली जगह ढूँढिए।")

    def test_cut_off_hint_names_directions(self):
        self.assertEqual(phrases.aiming_hint("en", "cut_off", ["left", "up"]),
                         "Text may be cut off. Move the phone left and up.")
        self.assertEqual(phrases.aiming_hint("hi", "cut_off", ["right"]),
                         "लिखावट कटी हुई हो सकती है। फ़ोन को दाईं ओर ले जाइए।")

    def test_traffic_light_and_arrow(self):
        import numpy as np
        import cv2
        frame = np.zeros((300, 100, 3), np.uint8)
        cv2.circle(frame, (50, 50), 30, (0, 0, 255), -1)
        dets = [{"class_name": "traffic light", "bbox": [0, 0, 100, 300]}]
        out = self.signs.explain({"text": "", "lines": [], "hints": []}, dets, frame, "hi")
        self.assertEqual(out["summary"], "ट्रैफ़िक लाइट लाल है। रुकिए।")
        out = self.signs.explain({"text": "शौचालय →", "lines": [], "hints": []}, lang="hi")
        self.assertIn("तीर दाईं ओर इशारा करता है।", out["summary"])


if __name__ == "__main__":
    unittest.main()
