import base64
import binascii

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response

from app.firebase_auth import require_firebase_user
from pydantic import BaseModel, Field

from app.config import settings

router = APIRouter(prefix="/api/speech", tags=["speech"])
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
TTS_LANGUAGE_CODES = {
    "bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN",
    "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN",
}


class SpeechSynthesisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2500)
    language_code: str


@router.post("/synthesize")
async def synthesize_speech(payload: SpeechSynthesisRequest, current_user: dict = Depends(require_firebase_user)):
    if payload.language_code not in TTS_LANGUAGE_CODES:
        raise HTTPException(
            status_code=400,
            detail="Sarvam Bulbul currently supports Hindi, English, Bengali, Gujarati, Kannada, Malayalam, Marathi, Odia, Punjabi, Tamil and Telugu for speech generation.",
        )
    if settings.app_mode != "live":
        raise HTTPException(status_code=409, detail="Speech generation is disabled in demo mode. Configure live mode and a Sarvam API key.")
    if not settings.sarvam_api_key:
        raise HTTPException(status_code=503, detail="Sarvam API key is missing. Add SARVAM_API_KEY to backend/.env.")

    headers = {"api-subscription-key": settings.sarvam_api_key}
    body = {
        "text": payload.text,
        "target_language_code": payload.language_code,
        "language_code": payload.language_code,
        "model": "bulbul:v4-flash",
        "speaker": "simran_en_customer",
        "output_audio_codec": "wav",
    }
    # The public REST contract uses language_code; target_language_code is ignored
    # by REST TTS but is harmless for clients sharing a streaming configuration.
    body.pop("target_language_code", None)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
            response = await client.post(SARVAM_TTS_URL, headers=headers, json=body)
        if response.is_error:
            raise HTTPException(status_code=502, detail=f"Speech synthesis provider returned HTTP {response.status_code}.")
        result = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Speech generation timed out. Please try again.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach the speech generation provider.")
    except ValueError:
        raise HTTPException(status_code=502, detail="Speech generation provider returned an invalid response.")

    audios = result.get("audios")
    if not isinstance(audios, list) or not audios or not isinstance(audios[0], str):
        raise HTTPException(status_code=502, detail="Speech provider did not return audio.")
    try:
        audio_bytes = base64.b64decode(audios[0], validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=502, detail="Speech provider returned invalid audio data.")
    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )
