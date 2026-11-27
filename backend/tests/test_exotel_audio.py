import unittest

from app.exotel_audio import (
    decode_audio,
    encode_audio,
    normalize_audio_format,
)


class ExotelAudioCodecTests(unittest.TestCase):
    def test_normalizes_documented_formats(self):
        self.assertEqual(normalize_audio_format("audio/x-raw"), "linear16")
        self.assertEqual(normalize_audio_format("audio/x-mulaw;rate=8000"), "mulaw")
        self.assertEqual(normalize_audio_format("audio/x-raw;rate=8000;bits=16"), "linear16")
        self.assertEqual(normalize_audio_format("audio/basic"), "mulaw")
        self.assertEqual(normalize_audio_format("mulaw"), "mulaw")

    def test_rejects_unknown_format(self):
        with self.assertRaises(ValueError):
            normalize_audio_format("audio/opus")

    def test_linear16_round_trip_is_byte_exact(self):
        pcm = b"\x00\x00\xe8\x03\x18\xfc"
        self.assertEqual(decode_audio(encode_audio(pcm, "audio/x-raw"), "audio/x-raw"), pcm)

    def test_mulaw_silence_vector(self):
        self.assertEqual(encode_audio(b"\x00\x00", "audio/x-mulaw"), b"\xff")
        self.assertEqual(decode_audio(b"\xff", "audio/x-mulaw"), b"\x00\x00")

    def test_mulaw_round_trip_is_bounded_and_keeps_sample_count(self):
        samples = [-12000, -3000, -500, 0, 500, 3000, 12000]
        pcm = b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples)
        encoded = encode_audio(pcm, "audio/x-mulaw")
        decoded = decode_audio(encoded, "audio/x-mulaw")
        self.assertEqual(len(decoded), len(pcm))
        decoded_samples = [
            int.from_bytes(decoded[i:i + 2], "little", signed=True)
            for i in range(0, len(decoded), 2)
        ]
        for original, restored in zip(samples, decoded_samples):
            self.assertLessEqual(abs(original - restored), 1100)

    def test_rejects_incomplete_linear16_sample(self):
        with self.assertRaises(ValueError):
            decode_audio(b"\x01", "audio/x-raw")


if __name__ == "__main__":
    unittest.main()
