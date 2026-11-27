"""Outbound PSTN call initiation through Exotel Voice V1.

The call path is intentionally feature-flagged. Do not enable it until the
public media WebSocket and bidirectional translation worker are deployed and
tested; otherwise the parties could be connected without translation.
"""
import re
import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.languages import LANGUAGE_CODES, TTS_LANGUAGE_CODES

router = APIRouter(prefix="/api/calls", tags=["calls"])
E164_INDIA = re.compile(r"^\+91[6-9]\d{9}$")
# Deliberately false until per-participant media routing is implemented.
MEDIA_BRIDGE_IMPLEMENTED = False


class StartCallRequest(BaseModel):
    caller_number: str = Field(description="The VaaniSetu user's phone number in +91 format")
    recipient_number: str = Field(description="The other participant's phone number in +91 format")
    source_language: str = "te-IN"
    target_language: str = "hi-IN"
    consent_confirmed: bool = False


@router.post("/start", status_code=status.HTTP_202_ACCEPTED)
async def start_call(request: StartCallRequest):
    """Ask Exotel to call the user first, then the recipient, and bridge them."""
    if not request.consent_confirmed:
        raise HTTPException(status_code=400, detail="Confirm that both participants have agreed to an AI-translated call.")
    if not E164_INDIA.fullmatch(request.caller_number) or not E164_INDIA.fullmatch(request.recipient_number):
        raise HTTPException(status_code=400, detail="Both phone numbers must be valid Indian mobile numbers in +91XXXXXXXXXX format.")
    if request.caller_number == request.recipient_number:
        raise HTTPException(status_code=400, detail="Caller and recipient numbers must be different.")
    if request.source_language not in LANGUAGE_CODES or request.target_language not in TTS_LANGUAGE_CODES:
        raise HTTPException(status_code=400, detail="The selected language direction is not currently supported for speech output.")
    if request.source_language == request.target_language:
        raise HTTPException(status_code=400, detail="Choose two different languages.")

    # Prevent calls until the actual two-way media bridge exists and has passed tests.
    if not MEDIA_BRIDGE_IMPLEMENTED:
        raise HTTPException(
            status_code=503,
            detail="The phone-call media bridge is still under development. No call has been placed.",
        )

    # Prevent accidental/unauthorized paid PSTN calls before production readiness.
    if not settings.enable_outbound_calls:
        raise HTTPException(
            status_code=503,
            detail="Phone calling is not enabled yet. The telephony media bridge must be deployed and tested first.",
        )

    required = (
        settings.exotel_api_key,
        settings.exotel_api_token,
        settings.exotel_account_sid,
        settings.exotel_caller_id,
        settings.exotel_stream_url,
    )
    if not all(required):
        raise HTTPException(status_code=503, detail="Exotel credentials and the public media WebSocket URL are not configured.")

    url = f"{settings.exotel_base_url.rstrip('/')}/v1/Accounts/{settings.exotel_account_sid}/Calls/connect"
    form_data = {
        "From": request.caller_number,
        "To": request.recipient_number,
        "CallerId": settings.exotel_caller_id,
        "StreamUrl": settings.exotel_stream_url,
        "StreamBegin": "at Leg1Connect",
        "TimeLimit": str(settings.max_call_seconds),
        "Record": "false",
        "CustomField": f"vaanisetu:{request.source_language}:{request.target_language}",
    }
    if settings.exotel_status_callback_url:
        form_data["StatusCallback"] = settings.exotel_status_callback_url
        form_data["StatusCallbackEvents"] = "answered terminal"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                url,
                data=form_data,
                auth=(settings.exotel_api_key, settings.exotel_api_token),
            )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        # Do not return provider response bodies: they may contain sensitive metadata.
        raise HTTPException(status_code=502, detail=f"Exotel rejected the call request (HTTP {exc.response.status_code}).") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Could not reach Exotel or parse its response.") from exc

    call = payload.get("Call", {})
    call_sid = call.get("Sid")
    if not call_sid:
        raise HTTPException(status_code=502, detail="Exotel did not return a call identifier.")
    return {
        "call_id": call_sid,
        "status": call.get("Status", "queued"),
        "message": "Call request accepted. Exotel will call your phone first, then the recipient.",
        "translation": {
            "source_language": request.source_language,
            "target_language": request.target_language,
        },
    }


@router.get("/provider-status")
async def provider_status():
    """Expose readiness without revealing credentials or phone numbers."""
    credentials_configured = all((
        settings.exotel_api_key,
        settings.exotel_api_token,
        settings.exotel_account_sid,
        settings.exotel_caller_id,
    ))
    media_endpoint_configured = bool(settings.exotel_stream_url and settings.exotel_media_token)
    return {
        "provider": "exotel",
        "credentials_configured": credentials_configured,
        "media_endpoint_configured": media_endpoint_configured,
        "outbound_calls_enabled": settings.enable_outbound_calls,
        "media_bridge_ready": False,
        "agentstream_protocol_verified": settings.exotel_agentstream_protocol_verified,
        "note": "The media relay and ExoML call orchestration are not production-ready. AgentStream protocol verification is an explicit prerequisite. No calls should be enabled.",
    }
