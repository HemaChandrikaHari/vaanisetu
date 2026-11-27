import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env when running from the backend directory or repository root.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@dataclass(frozen=True)
class Settings:
    app_mode: str = os.getenv("APP_MODE", "demo").strip().lower()
    sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "").strip()
    frontend_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS", "http://localhost:5173"
        ).split(",")
        if origin.strip()
    )


settings = Settings()

if settings.app_mode not in {"demo", "live"}:
    raise ValueError("APP_MODE must be either 'demo' or 'live'")
