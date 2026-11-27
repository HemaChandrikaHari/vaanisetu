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
    exotel_api_key: str = os.getenv("EXOTEL_API_KEY", "").strip()
    exotel_api_token: str = os.getenv("EXOTEL_API_TOKEN", "").strip()
    exotel_account_sid: str = os.getenv("EXOTEL_ACCOUNT_SID", "").strip()
    exotel_caller_id: str = os.getenv("EXOTEL_CALLER_ID", "").strip()
    exotel_base_url: str = os.getenv("EXOTEL_BASE_URL", "https://api.in.exotel.com").strip()
    exotel_stream_url: str = os.getenv("EXOTEL_STREAM_URL", "").strip()
    exotel_media_token: str = os.getenv("EXOTEL_MEDIA_TOKEN", "").strip()
    exotel_status_callback_url: str = os.getenv("EXOTEL_STATUS_CALLBACK_URL", "").strip()
    enable_outbound_calls: bool = os.getenv("ENABLE_OUTBOUND_CALLS", "false").strip().lower() == "true"
    max_call_seconds: int = int(os.getenv("MAX_CALL_SECONDS", "300"))


settings = Settings()

if settings.app_mode not in {"demo", "live"}:
    raise ValueError("APP_MODE must be either 'demo' or 'live'")
