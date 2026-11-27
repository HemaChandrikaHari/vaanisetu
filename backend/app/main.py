from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title="VaaniSetu API",
    description="Backend foundation for Telugu-Hindi voice translation.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.frontend_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "VaaniSetu API",
        "status": "running",
        "mode": settings.app_mode,
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": settings.app_mode,
        "translation_pipeline": "not_implemented",
    }
