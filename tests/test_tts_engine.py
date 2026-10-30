"""Unit tests for the TTS queue rules, without playing any audio.

(tests/test_tts.py is the manual check that actually speaks.)
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules import tts_engine


class TestTTSQueue(unittest.TestCase):
    def setUp(self):
        # No worker thread: messages stay in the queue so we can inspect it
        patcher = mock.patch.object(tts_engine.threading.Thread, "start")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tts = tts_engine.TTSEngine()

    def queued(self):
        return list(self.tts.msg_queue.queue)

    def test_queue_never_grows_past_three(self):
        for i in range(10):
            self.tts.speak(f"msg {i}")
        self.assertEqual(self.queued(), ["msg 7", "msg 8", "msg 9"])

    def test_priority_clears_backlog(self):
        self.tts.speak("chair on your left")
        self.tts.speak("door ahead")
        self.tts.speak("Stop! person ahead", priority=True)
        self.assertEqual(self.queued(), ["Stop! person ahead"])

    def test_voice_matches_the_language(self):
        class Voice:
            def __init__(self, id, name, languages):
                self.id, self.name, self.languages = id, name, languages
        voices = [Voice("com.apple.voice.samantha", "Samantha", ["en_US"]),
                  Voice("com.apple.voice.lekha", "Lekha", ["hi_IN"])]
        self.assertEqual(tts_engine.TTSEngine.pick_voice(voices, "hi"), "com.apple.voice.lekha")
        # No hints for English, and no Hindi voice installed: leave the default voice alone
        self.assertIsNone(tts_engine.TTSEngine.pick_voice(voices, "en"))
        self.assertIsNone(tts_engine.TTSEngine.pick_voice(voices[:1], "hi"))

    def test_empty_text_is_ignored(self):
        self.tts.speak("")
        self.assertEqual(self.queued(), [])


if __name__ == "__main__":
    unittest.main()
