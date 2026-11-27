from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.languages import SUPPORTED_LANGUAGES
from app.speech import router as speech_router

app = FastAPI(title="VaaniSetu API", description="Backend for multilingual Indian-language voice translation.", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.frontend_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(speech_router)

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
        "capabilities": {
            "speech_to_text": "Sarvam Saaras v4",
            "translation": "Sarvam Translate v1",
            "speech_to_text_languages": 22,
            "translation_languages": 22,
            "note": "Text-to-speech coverage is tracked separately and will be added with the TTS milestone.",
        },
    }
