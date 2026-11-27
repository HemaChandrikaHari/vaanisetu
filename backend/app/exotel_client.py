"""Small, secret-safe Exotel Programmable Voice API client."""
from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class ExotelApiError(RuntimeError):
    pass


class ExotelClient:
    def __init__(self) -> None:
        if not all((settings.exotel_api_key, settings.exotel_api_token, settings.exotel_account_sid)):
            raise ExotelApiError("Exotel API credentials are not configured")
        self.base = (
            settings.exotel_exoml_base_url.rstrip("/")
            + "/v2/accounts/"
            + settings.exotel_account_sid
        )
        self.auth = (settings.exotel_api_key, settings.exotel_api_token)

    async def create_leg(self, contact_uri: str, event_endpoint: str, timeout: int = 30) -> str:
        payload = {
            "contact_uri": contact_uri,
            "exophone": settings.exotel_caller_id,
            "leg_event_endpoint": event_endpoint,
            "timeout": timeout,
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(f"{self.base}/legs", json=payload, auth=self.auth)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            suffix = f" (HTTP {status_code})" if status_code else ""
            raise ExotelApiError(f"Exotel leg creation failed{suffix}") from exc

        leg_sid = self._find_sid(body)
        if not leg_sid:
            raise ExotelApiError("Exotel response did not contain a leg SID")
        return leg_sid

    async def start_stream(self, leg_sid: str, stream_url: str) -> None:
        payload = {
            "direction": "bidirectional",
            "url": stream_url,
            "content_type": settings.exotel_stream_content_type,
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.base}/legs/{leg_sid}/actions/start_stream",
                    json=payload,
                    auth=self.auth,
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            suffix = f" (HTTP {status_code})" if status_code else ""
            raise ExotelApiError(f"Exotel failed to start the media stream{suffix}") from exc

    async def hangup_leg(self, leg_sid: str) -> None:
        payload = {"exoml": "<Flow><Hangup></Hangup></Flow>"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base}/legs/{leg_sid}/actions",
                    json=payload,
                    auth=self.auth,
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            suffix = f" (HTTP {status_code})" if status_code else ""
            raise ExotelApiError(f"Exotel hangup action failed{suffix}") from exc

    @staticmethod
    def _find_sid(value: Any) -> str | None:
        if isinstance(value, dict):
            for key in ("leg_sid", "LegSid", "sid", "Sid"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
            for child in value.values():
                found = ExotelClient._find_sid(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = ExotelClient._find_sid(child)
                if found:
                    return found
        return None
