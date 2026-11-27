"""Exotel audio wire-format adapters.

The relay uses mono 8 kHz signed 16-bit little-endian PCM internally.
Exotel's docs describe both linear16 PCM and G.711 mu-law stream formats;
the account's selected format must still be confirmed before enabling calls.
"""
import struct

BIAS = 0x84
CLIP = 32635


def normalize_audio_format(value: str | None) -> str:
    """Normalize documented content types to the two supported wire codecs."""
    value = (value or "audio/x-raw").strip().lower()
    media_type = value.split(";", 1)[0].strip()
    if media_type in {"linear16", "audio/x-raw", "audio/l16", "audio/pcm", "audio/x-pcm"}:
        return "linear16"
    if media_type in {"mulaw", "audio/x-mulaw", "audio/mulaw", "audio/basic", "audio/pcmu"}:
        return "mulaw"
    raise ValueError(f"Unsupported Exotel audio format: {value}")


def _decode_mulaw_byte(value: int) -> int:
    value = (~value) & 0xFF
    sign = value & 0x80
    exponent = (value >> 4) & 0x07
    mantissa = value & 0x0F
    sample = ((mantissa << 3) + BIAS) << exponent
    sample -= BIAS
    return -sample if sign else sample


def _encode_mulaw_sample(sample: int) -> int:
    sample = max(-CLIP, min(CLIP, sample))
    sign = 0x80 if sample < 0 else 0
    if sample < 0:
        sample = -sample
    sample += BIAS
    exponent = 7
    mask = 0x4000
    while exponent > 0 and not (sample & mask):
        exponent -= 1
        mask >>= 1
    mantissa = (sample >> (exponent + 3)) & 0x0F
    return (~(sign | (exponent << 4) | mantissa)) & 0xFF


def decode_audio(payload: bytes, audio_format: str | None) -> bytes:
    """Decode Exotel wire audio into mono 8 kHz signed 16-bit little-endian PCM."""
    codec = normalize_audio_format(audio_format)
    if codec == "linear16":
        if len(payload) % 2:
            raise ValueError("Linear16 audio payload must contain complete 16-bit samples")
        return payload
    return b"".join(
        struct.pack("<h", _decode_mulaw_byte(byte))
        for byte in payload
    )


def encode_audio(pcm: bytes, audio_format: str | None) -> bytes:
    """Encode internal mono 8 kHz PCM into the selected Exotel wire codec."""
    if len(pcm) % 2:
        raise ValueError("PCM audio must contain complete 16-bit samples")
    codec = normalize_audio_format(audio_format)
    if codec == "linear16":
        return pcm
    return bytes(
        _encode_mulaw_sample(sample[0])
        for sample in struct.iter_unpack("<h", pcm)
    )
