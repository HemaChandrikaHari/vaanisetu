"""Provider-neutral PCM framing and speech-turn segmentation utilities.

These helpers do not define or assume an Exotel wire protocol. They operate
only after a verified adapter has decoded provider audio into mono 8 kHz,
16-bit little-endian PCM.
"""
from dataclasses import dataclass, field
import math

SAMPLE_RATE = 8000
FRAME_MS = 20
SAMPLE_WIDTH_BYTES = 2
FRAME_BYTES = SAMPLE_RATE * FRAME_MS // 1000 * SAMPLE_WIDTH_BYTES


def pcm_rms(pcm: bytes) -> float:
    """Return RMS amplitude for signed 16-bit little-endian PCM bytes."""
    usable = len(pcm) - (len(pcm) % SAMPLE_WIDTH_BYTES)
    if usable == 0:
        return 0.0
    count = usable // SAMPLE_WIDTH_BYTES
    total = 0
    for offset in range(0, usable, SAMPLE_WIDTH_BYTES):
        sample = int.from_bytes(pcm[offset:offset + 2], "little", signed=True)
        total += sample * sample
    return math.sqrt(total / count)


@dataclass
class AudioTurnSegmenter:
    """Split arbitrarily chunked PCM into bounded turns without dropping tails."""
    silence_threshold: float = 420
    end_silence_ms: int = 600
    minimum_speech_ms: int = 300
    maximum_speech_ms: int = 9000
    pending: bytearray = field(default_factory=bytearray)
    turn: bytearray = field(default_factory=bytearray)
    speech_started: bool = False
    silence_ms: int = 0
    speech_ms: int = 0

    def feed(self, chunk: bytes) -> list[bytes]:
        self.pending.extend(chunk)
        completed: list[bytes] = []
        while len(self.pending) >= FRAME_BYTES:
            frame = bytes(self.pending[:FRAME_BYTES])
            del self.pending[:FRAME_BYTES]
            loud = pcm_rms(frame) >= self.silence_threshold

            if loud:
                self.speech_started = True
                self.silence_ms = 0
                self.speech_ms += FRAME_MS
                self.turn.extend(frame)
            elif self.speech_started:
                self.silence_ms += FRAME_MS
                self.turn.extend(frame)

            ended_by_silence = self.speech_started and self.silence_ms >= self.end_silence_ms
            ended_by_limit = self.speech_started and self.speech_ms >= self.maximum_speech_ms
            if ended_by_silence or ended_by_limit:
                if self.speech_ms >= self.minimum_speech_ms and self.turn:
                    completed.append(bytes(self.turn))
                self._reset_turn()
        return completed

    def flush(self) -> bytes | None:
        """Return a valid in-progress turn at stream shutdown, if one exists."""
        if self.pending:
            # Do not fabricate a partial PCM sample/frame at shutdown.
            self.pending.clear()
        result = bytes(self.turn) if self.speech_ms >= self.minimum_speech_ms and self.turn else None
        self._reset_turn()
        return result

    def _reset_turn(self) -> None:
        self.turn.clear()
        self.speech_started = False
        self.silence_ms = 0
        self.speech_ms = 0
