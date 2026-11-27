"""Feature-gated two-leg Exotel call orchestration.

The two PSTN legs remain separate: VaaniSetu translates caller audio and sends
it to the recipient's stream, and vice versa. It deliberately does not join
the original audio legs into a conference bridge, which would leak untranslated
speech to the other participant.
"""
import asyncio
import re
import secrets
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

from app.config import settings
from app.exotel_client import ExotelApiError, ExotelClient
from app.languages import LANGUAGE_CODES, TTS_LANGUAGE_CODES

router = APIRouter(prefix="/api/calls", tags=["calls"])
security = HTTPBasic(auto_error=False)
E164_INDIA = re.compile(r"^\+91[6-9]\d{9}$")

# A real PSTN translation test is still required before changing this constant.
MEDIA_BRIDGE_IMPLEMENTED = False
CALL_SESSIONS: dict[str, dict[str, Any]] = {}
CALL_SESSIONS_LOCK = asyncio.Lock()


class StartCallRequest(BaseModel):
    caller_number: str = Field(description="The VaaniSetu user's phone number in +91 format")
    recipient_number: str = Field(description="The other participant's phone number in +91 format")
    source_language: str = "te-IN"
    target_language: str = "hi-IN"
    consent_confirmed: bool = False


def _callback_url(session_id: str, role: str, source: str, target: str) -> str:
    query = urlencode({
        "session_id": session_id,
        "role": role,
        "source_language": source,
        "target_language": target,
    })
    return f"{settings.exotel_leg_event_endpoint_url}?{query}"


def _stream_url(session_id: str, role: str, source: str, target: str) -> str:
    query = urlencode({
        "token": settings.exotel_media_token,
        "session_id": session_id,
        "source_language": source,
        "target_language": target,
    })
    return f"{settings.exotel_stream_url.rstrip('/')}/{role}?{query}"


def _valid_event_credentials(credentials: HTTPBasicCredentials | None) -> bool:
    username = settings.exotel_event_auth_username
    password = settings.exotel_event_auth_password
    return bool(
        credentials and username and password
        and secrets.compare_digest(credentials.username, username)
        and secrets.compare_digest(credentials.password, password)
    )


async def _process_exotel_event(
    session_id: str,
    role: str,
    source: str,
    target: str,
    event_name: str,
    leg_sid: str,
) -> None:
    async with CALL_SESSIONS_LOCK:
        session = CALL_SESSIONS.get(session_id)
        if not session:
            return
        if role not in session["roles"]:
            return
        if event_name == "leg_answered":
            session["roles"][role]["leg_sid"] = leg_sid
        elif event_name in {"leg_terminated", "leg_failed_to_create"}:
            other_legs = [
                details.get("leg_sid")
                for other_role, details in session["roles"].items()
                if other_role != role and details.get("leg_sid")
            ]
            session["ended"] = True
            # If a callback arrives while POST /legs is still returning, retain
            # the session so the creator can hang up any leg created afterward.
            if not session.get("creating", False):
                session["cleanup_pending"] = True
        else:
            return

    client = ExotelClient()
    if event_name == "leg_answered":
        stream_url = _stream_url(session_id, role, source, target)
        try:
            await client.start_stream(leg_sid, stream_url)
        except ExotelApiError:
            # Fail closed: do not leave a silent or untranslated connected call.
            await client.hangup_leg(leg_sid)
            async with CALL_SESSIONS_LOCK:
                current = CALL_SESSIONS.get(session_id)
                if current:
                    current["ended"] = True
            raise
        return

    for other_leg_sid in other_legs:
        try:
            await client.hangup_leg(other_leg_sid)
        except ExotelApiError:
            # The other leg may already have terminated.
            pass
    async with CALL_SESSIONS_LOCK:
        CALL_SESSIONS.pop(session_id, None)


@router.post("/start", status_code=status.HTTP_202_ACCEPTED)
async def start_call(request: StartCallRequest):
    """Initiate two independent PSTN legs, one for each participant."""
    if not request.consent_confirmed:
        raise HTTPException(status_code=400, detail="Confirm that both participants have agreed to an AI-translated call.")
    if not E164_INDIA.fullmatch(request.caller_number) or not E164_INDIA.fullmatch(request.recipient_number):
        raise HTTPException(status_code=400, detail="Both phone numbers must be valid Indian mobile numbers in +91XXXXXXXXXX format.")
    if request.caller_number == request.recipient_number:
        raise HTTPException(status_code=400, detail="Caller and recipient numbers must be different.")
    if request.source_language not in LANGUAGE_CODES or request.target_language not in TTS_LANGUAGE_CODES:
        raise HTTPException(status_code=400, detail="The selected language direction is not currently supported for speech output.")
    if request.source_language not in TTS_LANGUAGE_CODES or request.source_language == request.target_language:
        raise HTTPException(status_code=400, detail="Both languages must support speech output and must be different.")

    # Keep all paid calls blocked until Exotel confirms the account-specific
    # event transport, stream protocol and the end-to-end media bridge is tested.
    if not MEDIA_BRIDGE_IMPLEMENTED:
        raise HTTPException(
            status_code=503,
            detail="The two-leg call controller is staged, but live media bridging has not passed an Exotel PSTN test. No call has been placed.",
        )
    if not settings.enable_outbound_calls:
        raise HTTPException(status_code=503, detail="Outbound calling is disabled.")
    if not (
        settings.exotel_agentstream_protocol_verified
        and settings.exotel_leg_event_endpoint_verified
        and settings.exotel_leg_event_endpoint_url.startswith("https://")
        and settings.exotel_stream_url.startswith("wss://")
        and settings.exotel_media_token
        and settings.exotel_event_auth_username
        and settings.exotel_event_auth_password
        and settings.exotel_caller_id
    ):
        raise HTTPException(status_code=503, detail="Exotel event transport, AgentStream, callback authentication and secure media endpoint must be verified and configured first.")

    session_id = secrets.token_urlsafe(24)
    async with CALL_SESSIONS_LOCK:
        CALL_SESSIONS[session_id] = {
            "roles": {
                "caller": {"leg_sid": None},
                "recipient": {"leg_sid": None},
            },
            "ended": False,
            "creating": True,
            "cleanup_pending": False,
        }

    client = ExotelClient()
    caller_callback = _callback_url(
        session_id, "caller", request.source_language, request.target_language
    )
    recipient_callback = _callback_url(
        session_id, "recipient", request.source_language, request.target_language
    )
    results = await asyncio.gather(
        client.create_leg(request.caller_number, caller_callback),
        client.create_leg(request.recipient_number, recipient_callback),
        return_exceptions=True,
    )
    created_legs = [result for result in results if isinstance(result, str)]
    failures = [result for result in results if isinstance(result, BaseException)]
    if failures:
        for leg_sid in created_legs:
            try:
                await client.hangup_leg(leg_sid)
            except ExotelApiError:
                pass
        async with CALL_SESSIONS_LOCK:
            CALL_SESSIONS.pop(session_id, None)
        raise HTTPException(status_code=502, detail="Exotel could not create both call legs; any successfully created leg was asked to hang up.")

    async with CALL_SESSIONS_LOCK:
        current = CALL_SESSIONS.get(session_id)
        if current is None:
            current = {
                "roles": {"caller": {"leg_sid": None}, "recipient": {"leg_sid": None}},
                "ended": True,
                "creating": False,
                "cleanup_pending": True,
            }
            CALL_SESSIONS[session_id] = current
        current["roles"]["caller"]["leg_sid"] = results[0]
        current["roles"]["recipient"]["leg_sid"] = results[1]
        current["creating"] = False
        cleanup_now = current.get("cleanup_pending", False) or current.get("ended", False)

    if cleanup_now:
        for leg_sid in created_legs:
            try:
                await client.hangup_leg(leg_sid)
            except ExotelApiError:
                pass
        async with CALL_SESSIONS_LOCK:
            CALL_SESSIONS.pop(session_id, None)
        raise HTTPException(status_code=502, detail="A participant ended or a leg failed during setup. Any created legs were asked to hang up.")

    return {
        "call_id": session_id,
        "status": "initiated",
        "message": "Exotel is dialing both participants independently. Translation starts after each leg answers and its bidirectional stream is ready.",
        "translation": {
            "source_language": request.source_language,
            "target_language": request.target_language,
        },
    }


@router.post("/exotel/events", status_code=200)
async def exotel_event(
    background_tasks: BackgroundTasks,
    event: dict[str, Any],
    session_id: str = Query(..., min_length=16, max_length=80),
    role: str = Query(..., pattern="^(caller|recipient)$"),
    source_language: str = Query(...),
    target_language: str = Query(...),
    credentials: HTTPBasicCredentials | None = Depends(security),
):
    """Acknowledge Exotel HTTPS events quickly; process actions in background."""
    if not settings.exotel_leg_event_endpoint_verified:
        raise HTTPException(status_code=503, detail="Exotel HTTPS event endpoint is not verified for this account.")
    if not _valid_event_credentials(credentials):
        raise HTTPException(
            status_code=401,
            detail="Invalid event endpoint credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )
    if source_language not in TTS_LANGUAGE_CODES or target_language not in TTS_LANGUAGE_CODES:
        raise HTTPException(status_code=400, detail="Unsupported event language configuration.")

    event_name = str(event.get("event_name") or "")
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    leg_sid = str(data.get("leg_sid") or "")
    if event_name in {"leg_answered", "leg_terminated"} and not leg_sid:
        raise HTTPException(status_code=400, detail="The Exotel event is missing data.leg_sid.")

    if event_name in {"leg_answered", "leg_terminated", "leg_failed_to_create"}:
        background_tasks.add_task(
            _process_exotel_event,
            session_id,
            role,
            source_language,
            target_language,
            event_name,
            leg_sid,
        )
    return {"received": True}


@router.get("/provider-status")
async def provider_status():
    """Expose readiness without revealing credentials, phone numbers or tokens."""
    credentials_configured = all((
        settings.exotel_api_key,
        settings.exotel_api_token,
        settings.exotel_account_sid,
        settings.exotel_caller_id,
    ))
    media_endpoint_configured = bool(
        settings.exotel_stream_url.startswith("wss://")
        and settings.exotel_media_token
    )
    return {
        "provider": "exotel",
        "credentials_configured": credentials_configured,
        "media_endpoint_configured": media_endpoint_configured,
        "leg_event_endpoint_configured": settings.exotel_leg_event_endpoint_url.startswith("https://"),
        "leg_event_endpoint_verified": settings.exotel_leg_event_endpoint_verified,
        "outbound_calls_enabled": settings.enable_outbound_calls,
        "media_bridge_ready": False,
        "agentstream_protocol_verified": settings.exotel_agentstream_protocol_verified,
        "note": "The two-leg call controller and HTTPS event adapter are staged. The AgentStream Legs API guide specifies gRPC leg events while the ExoML guide specifies HTTPS callbacks; the transport must be confirmed for this account. The end-to-end PSTN media relay is not yet verified. No calls should be enabled.",
    }
