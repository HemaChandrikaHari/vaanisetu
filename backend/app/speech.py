import httpx
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.config import settings
from app.languages import LANGUAGE_CODES

router = APIRouter(prefix="/api/speech", tags=["speech"])
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
MAX_AUDIO_BYTES = 10 * 1024 * 1024


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language_code: str = Query(default="te-IN"),
):
    """Transcribe one short audio turn. Audio is processed in memory, not saved."""
    if language_code not in LANGUAGE_CODES:
        raise HTTPException(status_code=400, detail="Unsupported language code. Use GET /api/languages.")
    if settings.app_mode != "live":
        raise HTTPException(
            status_code=409,
            detail="Speech recognition is disabled in demo mode. Set APP_MODE=live and SARVAM_API_KEY in backend/.env, then restart the backend.",
        )
    if not settings.sarvam_api_key:
        raise HTTPException(status_code=503, detail="Sarvam API key is missing. Add SARVAM_API_KEY to backend/.env.")

    audio_bytes = await file.read(MAX_AUDIO_BYTES + 1)
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="The uploaded audio is empty.")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file is too large. Maximum size is 10 MB.")

    content_type = (file.content_type or "application/octet-stream").split(";")[0]
    filename = file.filename or "recording.webm"
    headers = {"api-subscription-key": settings.sarvam_api_key}
    data = {"model": "saaras:v4", "language_code": language_code, "mode": "transcribe"}
    files = {"file": (filename, audio_bytes, content_type)}

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=15.0)) as client:
            response = await client.post(SARVAM_STT_URL, headers=headers, data=data, files=files)
        if response.is_error:
            raise HTTPException(
                status_code=502,
                detail=f"Speech provider returned HTTP {response.status_code}. Check API access and audio format.",
            )
        result = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Speech recognition timed out. Try a shorter recording.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach the speech recognition provider.")
    except ValueError:
        raise HTTPException(status_code=502, detail="Speech provider returned an invalid response.")

    transcript = result.get("transcript")
    if not isinstance(transcript, str):
        raise HTTPException(status_code=502, detail="Speech provider response did not contain a transcript.")
    return {
        "transcript": transcript,
        "language_code": result.get("language_code") or language_code,
        "request_id": result.get("request_id"),
        "provider": "sarvam",
        "model": "saaras:v4",
    }
