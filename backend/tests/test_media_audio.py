import unittest

from app.audio_processing import AudioTurnSegmenter, FRAME_BYTES, pcm_rms


def pcm_frame(sample: int) -> bytes:
    return int(sample).to_bytes(2, "little", signed=True) * (FRAME_BYTES // 2)


class AudioTurnSegmenterTests(unittest.TestCase):
    def test_rms_handles_empty_and_known_signal(self):
        self.assertEqual(pcm_rms(b""), 0.0)
        self.assertAlmostEqual(pcm_rms(pcm_frame(1000)), 1000.0)

    def test_preserves_frames_across_arbitrary_network_chunks(self):
        segmenter = AudioTurnSegmenter()
        speech = pcm_frame(1000) * 20
        silence = pcm_frame(0) * 30
        stream = speech + silence
        outputs = []
        # Deliberately split in the middle of samples and 20 ms frames.
        for start in range(0, len(stream), 137):
            outputs.extend(segmenter.feed(stream[start:start + 137]))
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0], stream)
        self.assertEqual(segmenter.pending, bytearray())

    def test_short_noise_is_discarded(self):
        segmenter = AudioTurnSegmenter()
        result = segmenter.feed(pcm_frame(1000) * 5 + pcm_frame(0) * 30)
        self.assertEqual(result, [])

    def test_long_speech_is_split_at_configured_limit_without_loss(self):
        segmenter = AudioTurnSegmenter(maximum_speech_ms=100, minimum_speech_ms=40)
        speech = pcm_frame(1000) * 15
        outputs = segmenter.feed(speech)
        self.assertEqual(len(outputs), 3)
        self.assertTrue(all(len(turn) == 5 * FRAME_BYTES for turn in outputs))
        self.assertEqual(b"".join(outputs), speech)
        self.assertIsNone(segmenter.flush())

    def test_flush_returns_in_progress_valid_turn(self):
        segmenter = AudioTurnSegmenter()
        speech = pcm_frame(1000) * 20
        self.assertEqual(segmenter.feed(speech), [])
        self.assertEqual(segmenter.flush(), speech)
        self.assertIsNone(segmenter.flush())


if __name__ == "__main__":
    unittest.main()
