"""Standalone test script for Text-to-Speech audio queue.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.tts_engine import TTSEngine


def test_speech():
    print("Initializing TTS engine test...")
    tts = TTSEngine()

    print("Sending non-blocking spoken instructions...")
    tts.speak("System test initiated")
    time.sleep(1.2)

    tts.speak("Chair on your left")
    time.sleep(1.2)

    tts.speak("Stop! Obstacle directly ahead", priority=True)
    time.sleep(1.8)

    tts.stop()
    print("Audio test finished successfully.")


if __name__ == "__main__":
    test_speech()
