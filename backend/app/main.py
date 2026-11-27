from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.languages import SUPPORTED_LANGUAGES, TTS_LANGUAGES
from app.speech import router as speech_router
from app.translation import router as translation_router
from app.tts import router as tts_router
from app.telephony import router as telephony_router
from app.media_bridge import router as media_bridge_router

app = FastAPI(title="VaaniSetu API", description="Backend for multilingual Indian-language voice translation.", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(set(settings.frontend_origins) | {"https://localhost", "capacitor://localhost"}),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(speech_router)
app.include_router(translation_router)
app.include_router(tts_router)
app.include_router(telephony_router)
app.include_router(media_bridge_router)

@app.get("/")
async def root():
    return {"name": "VaaniSetu API", "status": "running", "mode": settings.app_mode}

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": settings.app_mode,
        "sarvam_configured": bool(settings.sarvam_api_key),
        "speech_recognition": "ready" if settings.app_mode == "live" and settings.sarvam_api_key else "demo_only",
    }

@app.get("/api/languages")
async def get_languages():
    return {
        "languages": SUPPORTED_LANGUAGES,
        "tts_languages": TTS_LANGUAGES,
        "capabilities": {
            "speech_to_text": "Sarvam Saaras v4",
            "translation": "Sarvam Translate v1",
            "text_to_speech": "Sarvam Bulbul v4 Flash",
            "speech_to_text_languages": 23,
            "translation_languages": 23,
            "scheduled_indian_languages": 22,
            "text_to_speech_languages": 11,
        },
    }
