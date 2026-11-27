"""Prototype Exotel media relay for one translated utterance at a time.

This is deliberately not marked production-ready: Exotel call-leg creation,
bridge orchestration, public TLS deployment, and real-call validation remain
separate gates.
"""
import asyncio
import base64
import io
import json
import logging
import re
import secrets
import wave
from dataclasses import dataclass, field
from typing import Optional

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.audio_processing import AudioTurnSegmenter, SAMPLE_RATE

logger = logging.getLogger(__name__)
router = APIRouter(tags=["media-bridge"])

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

@dataclass
class Participant:
    websocket: WebSocket
    stream_sid: str
    role: str
    source_language: str
    target_language: str
    segmenter: AudioTurnSegmenter = field(default_factory=AudioTurnSegmenter)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

SESSIONS: dict[str, dict[str, Participant]] = {}
SESSIONS_LOCK = asyncio.Lock()


def _wav_8khz(pcm: bytes) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm)
    return output.getvalue()


def _wav_to_pcm(audio: bytes) -> bytes:
    with wave.open(io.BytesIO(audio), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getframerate() != 8000:
            raise ValueError("TTS audio must be mono 16-bit PCM at 8 kHz")
        return wav.readframes(wav.getnframes())


async def _translate_turn(pcm: bytes, source: str, target: str) -> bytes:
    if not settings.sarvam_api_key:
        raise RuntimeError("Sarvam API key is not configured")
    headers = {"api-subscription-key": settings.sarvam_api_key}
    async with httpx.AsyncClient(timeout=httpx.Timeout(35.0, connect=10.0)) as client:
        stt = await client.post(
            SARVAM_STT_URL,
            headers=headers,
            data={"model": "saaras:v4", "language_code": source, "mode": "transcribe"},
            files={"file": ("turn.wav", _wav_8khz(pcm), "audio/wav")},
        )
        stt.raise_for_status()
        transcript = stt.json().get("transcript", "").strip()
        if not transcript:
            return b""

        translated_response = await client.post(
            SARVAM_TRANSLATE_URL,
            headers=headers,
            json={
                "input": transcript,
                "source_language_code": source,
                "target_language_code": target,
                "model": "sarvam-translate:v1",
                "mode": "formal",
            },
        )
        translated_response.raise_for_status()
        translated = translated_response.json().get("translated_text", "").strip()
        if not translated:
            return b""

        tts = await client.post(
            SARVAM_TTS_URL,
            headers=headers,
            json={
                "text": translated,
                "model": "bulbul:v4-flash",
                "language_code": target,
                "speaker": "simran_en_customer",
                "speech_sample_rate": 8000,
                "output_audio_codec": "wav",
            },
        )
        tts.raise_for_status()
        audio_b64 = tts.json().get("audios", [""])[0]
        return _wav_to_pcm(base64.b64decode(audio_b64))


async def _relay_turn(call_sid: str, sender: Participant, pcm: bytes) -> None:
    async with SESSIONS_LOCK:
        peer = SESSIONS.get(call_sid, {}).get("recipient" if sender.role == "caller" else "caller")
    if peer is None:
        logger.info("Peer stream not connected yet; translated turn was not relayed")
        return
    translated_pcm = await _translate_turn(pcm, sender.source_language, sender.target_language)
    if not translated_pcm:
        return
    # Candidate adapter payload shape only; do not enable until verified
    # against the account-specific AgentStream documentation and live tests.
    async with peer.lock:
        for offset in range(0, len(translated_pcm), 3200):
            chunk = translated_pcm[offset:offset + 3200]
            message = {
                "event": "media",
                "stream_sid": peer.stream_sid,
                "media": {"payload": base64.b64encode(chunk).decode("ascii")},
            }
            await peer.websocket.send_text(json.dumps(message))


async def _consume_audio(call_sid: str, participant: Participant, payload: str) -> None:
    raw = base64.b64decode(payload, validate=True)
    # This function is only valid after a verified adapter decodes provider
    # frames into mono 8 kHz signed 16-bit PCM.
    completed_turns = participant.segmenter.feed(raw)
    for turn in completed_turns:
        try:
            await _relay_turn(call_sid, participant, turn)
        except Exception:
            logger.exception("A media turn failed; audio was not retained")


@router.websocket("/api/calls/media/{role}")
async def exotel_media_stream(websocket: WebSocket, role: str):
    """Receive one Exotel participant stream and return translated peer audio."""
    if not settings.exotel_agentstream_protocol_verified:
        await websocket.close(code=1013, reason="Exotel AgentStream protocol has not been verified for this account")
        return
    if role not in {"caller", "recipient"}:
        await websocket.close(code=1008)
        return
    token = websocket.query_params.get("token", "")
    session_id = websocket.query_params.get("session_id", "")
    if (not settings.exotel_media_token
            or not secrets.compare_digest(token, settings.exotel_media_token)
            or not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", session_id)):
        await websocket.close(code=1008)
        return

    from app.languages import TTS_LANGUAGE_CODES
    source = websocket.query_params.get("source_language", "te-IN")
    target = websocket.query_params.get("target_language", "hi-IN")
    # Both directions need speech output, so both selected languages must
    # currently be supported by Bulbul TTS.
    if source not in TTS_LANGUAGE_CODES or target not in TTS_LANGUAGE_CODES or source == target:
        await websocket.close(code=1008, reason="Unsupported translation language direction")
        return
    if role == "recipient":
        source, target = target, source
    await websocket.accept()
    session_key = session_id
    participant: Optional[Participant] = None
    try:
        while True:
            raw_message = await websocket.receive_text()
            message = json.loads(raw_message)
            event = message.get("event")
            if event == "start":
                stream_sid = str(message.get("stream_sid") or message.get("start", {}).get("stream_sid") or "")
                if not stream_sid:
                    await websocket.close(code=1008)
                    return
                participant = Participant(websocket, stream_sid, role, source, target)
                async with SESSIONS_LOCK:
                    existing = SESSIONS.setdefault(session_key, {})
                    if role in existing:
                        await websocket.close(code=1008, reason="Participant stream already exists for this session")
                        return
                    existing[role] = participant
            elif event == "media" and participant and session_key:
                media = message.get("media", {})
                payload = media.get("payload")
                if payload:
                    await _consume_audio(session_key, participant, payload)
            elif event == "stop":
                if participant:
                    final_turn = participant.segmenter.flush()
                    if final_turn:
                        try:
                            await _relay_turn(session_key, participant, final_turn)
                        except Exception:
                            logger.exception("Final media turn failed during stream shutdown")
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Exotel media WebSocket failed")
    finally:
        if session_key:
            async with SESSIONS_LOCK:
                current = SESSIONS.get(session_key, {})
                if participant and current.get(role) is participant:
                    current.pop(role, None)
                if not current:
                    SESSIONS.pop(session_key, None)
