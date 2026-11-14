# Created at: 2026-11-14 04:59 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:59 EST
# Last Modified by: Codex
# Verifies strict audio lines, sequence ordering, and deterministic generated WAV assets.

import importlib.util
from pathlib import Path
import tempfile
import unittest
import wave


PROJECT_DIR = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "mac_audio_companion", PROJECT_DIR / "scripts/mac_audio_companion.py"
)
assert SPEC is not None and SPEC.loader is not None
audio = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audio)


class AudioProtocolTest(unittest.TestCase):
    def test_accepts_only_exact_bounded_schema(self) -> None:
        valid = (
            'CATAMAZE_AUDIO {"schema":"catamaze.audio.v1","seq":42,'
            '"tick":125,"event":"PLAYER_DAMAGE"}'
        )
        self.assertEqual(audio.parse_audio_line(valid)["event"], "PLAYER_DAMAGE")
        self.assertIsNone(audio.parse_audio_line("noise " + valid))
        self.assertIsNone(audio.parse_audio_line(valid[:-1]))
        self.assertIsNone(audio.parse_audio_line(valid[:-1] + ',"x":1}'))
        self.assertIsNone(audio.parse_audio_line(valid.replace("PLAYER_DAMAGE", "UNKNOWN")))
        self.assertIsNone(audio.parse_audio_line("CATAMAZE_AUDIO " + "x" * 129))

    def test_sequence_filter_handles_duplicates_stale_and_wrap(self) -> None:
        sequence = audio.SequenceFilter()
        self.assertTrue(sequence.accept(0xFFFFFFFE))
        self.assertFalse(sequence.accept(0xFFFFFFFE))
        self.assertTrue(sequence.accept(0xFFFFFFFF))
        self.assertTrue(sequence.accept(0))
        self.assertFalse(sequence.accept(0xFFFFFFFF))
        self.assertTrue(sequence.accept(3))

    def test_generates_all_mono_pcm_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            assets = audio.ensure_assets(Path(temporary))
            self.assertEqual(set(assets), audio.ALLOWED_EVENTS)
            for path in assets.values():
                with wave.open(str(path), "rb") as sound:
                    self.assertEqual(sound.getnchannels(), 1)
                    self.assertEqual(sound.getsampwidth(), 2)
                    self.assertEqual(sound.getframerate(), audio.SAMPLE_RATE)
                    self.assertGreater(sound.getnframes(), 1000)


if __name__ == "__main__":
    unittest.main()
