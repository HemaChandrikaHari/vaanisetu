import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.languages import LANGUAGE_CODES

router = APIRouter(prefix="/api/translation", tags=["translation"])
SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    source_language_code: str
    target_language_code: str


@router.post("/translate")
async def translate_text(payload: TranslationRequest):
    if payload.source_language_code not in LANGUAGE_CODES or payload.target_language_code not in LANGUAGE_CODES:
        raise HTTPException(status_code=400, detail="Unsupported language code. Use GET /api/languages.")
    if payload.source_language_code == payload.target_language_code:
        return {"translated_text": payload.text, "source_language_code": payload.source_language_code, "provider": "none"}
    if settings.app_mode != "live":
        raise HTTPException(status_code=409, detail="Translation is disabled in demo mode. Configure live mode and a Sarvam API key.")
    if not settings.sarvam_api_key:
        raise HTTPException(status_code=503, detail="Sarvam API key is missing. Add SARVAM_API_KEY to backend/.env.")

    headers = {"api-subscription-key": settings.sarvam_api_key}
    body = {
        "input": payload.text,
        "source_language_code": payload.source_language_code,
        "target_language_code": payload.target_language_code,
        "model": "sarvam-translate:v1",
        "mode": "formal",
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=15.0)) as client:
            response = await client.post(SARVAM_TRANSLATE_URL, headers=headers, json=body)
        if response.is_error:
            raise HTTPException(status_code=502, detail=f"Translation provider returned HTTP {response.status_code}.")
        result = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Translation timed out. Please try again.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach the translation provider.")
    except ValueError:
        raise HTTPException(status_code=502, detail="Translation provider returned an invalid response.")

    translated = result.get("translated_text")
    if not isinstance(translated, str) or not translated.strip():
        raise HTTPException(status_code=502, detail="Translation provider did not return translated text.")
    return {
        "translated_text": translated,
        "source_language_code": result.get("source_language_code") or payload.source_language_code,
        "request_id": result.get("request_id"),
        "provider": "sarvam",
        "model": "sarvam-translate:v1",
    }
