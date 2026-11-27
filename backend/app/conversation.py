"""Authenticated, ephemeral WebRTC signalling rooms for two-phone voice sessions.

Audio is exchanged directly between browsers/devices with WebRTC. This service
only authenticates participants and relays SDP/ICE signalling; it never stores
or receives microphone audio.
"""
import asyncio
import json
import logging
import secrets
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.firebase_auth import require_firebase_user

router = APIRouter(prefix="/api/conversation", tags=["conversation"])
ROOM_TTL_SECONDS = 2 * 60 * 60
MAX_SIGNAL_BYTES = 64 * 1024
logger = logging.getLogger(__name__)

ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

ROOMS: dict[str, dict[str, Any]] = {}
ROOMS_LOCK = asyncio.Lock()


class CreateRoomResponse(BaseModel):
    room_code: str
    expires_in_seconds: int


class CreateTicketResponse(BaseModel):
    ticket: str
    expires_in_seconds: int


def _new_room_code() -> str:
    return "".join(secrets.choice(ROOM_ALPHABET) for _ in range(8))


def _room_is_expired(room: dict[str, Any]) -> bool:
    return time.time() - room["created_at"] > ROOM_TTL_SECONDS


@router.post("/rooms", response_model=CreateRoomResponse)
async def create_room(user: dict = Depends(require_firebase_user)):
    async with ROOMS_LOCK:
        for code, room in list(ROOMS.items()):
            if _room_is_expired(room):
                ROOMS.pop(code, None)
        for _ in range(5):
            code = _new_room_code()
            if code not in ROOMS:
                ROOMS[code] = {
                    "created_by": user["uid"],
                    "created_at": time.time(),
                    "participants": {},
                    "tickets": {},
                }
                return {"room_code": code, "expires_in_seconds": ROOM_TTL_SECONDS}
    raise HTTPException(status_code=503, detail="Could not create a conversation room. Please try again.")


@router.post("/rooms/{room_code}/ticket", response_model=CreateTicketResponse)
async def issue_room_ticket(room_code: str, user: dict = Depends(require_firebase_user)):
    code = room_code.strip().upper()
    if len(code) != 8 or any(char not in ROOM_ALPHABET for char in code):
        raise HTTPException(status_code=404, detail="Room not found or expired.")
    async with ROOMS_LOCK:
        room = ROOMS.get(code)
        if room is None or _room_is_expired(room):
            raise HTTPException(status_code=404, detail="Room not found or expired.")
        uid = str(user.get("uid", ""))
        if not uid:
            raise HTTPException(status_code=401, detail="A valid sign-in is required.")
        if uid in room["participants"]:
            raise HTTPException(status_code=409, detail="This account is already in the room.")
        if len(room["participants"]) >= 2:
            raise HTTPException(status_code=409, detail="This room already has two participants.")
        now = time.time()
        for old_ticket, ticket_data in list(room["tickets"].items()):
            if ticket_data["expires_at"] < now:
                room["tickets"].pop(old_ticket, None)
        if len(room["tickets"]) >= 4:
            raise HTTPException(status_code=429, detail="Too many pending room joins. Wait a moment and try again.")
        ticket = secrets.token_urlsafe(32)
        room["tickets"][ticket] = {"uid": uid, "expires_at": now + 60}
        return {"ticket": ticket, "expires_in_seconds": 60}


async def _send_peer_event(room: dict[str, Any], sender_uid: str, message: dict) -> None:
    for uid, participant in list(room["participants"].items()):
        if uid != sender_uid:
            await participant["websocket"].send_json(message)


@router.websocket("/ws/{room_code}")
async def conversation_signalling(websocket: WebSocket, room_code: str):
    code = room_code.strip().upper()
    if len(code) != 8 or any(char not in ROOM_ALPHABET for char in code):
        await websocket.close(code=1008, reason="Invalid room code")
        return

    await websocket.accept()
    uid = None
    role = None
    try:
        auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        if not isinstance(auth_message, dict) or auth_message.get("type") != "auth":
            await websocket.close(code=1008, reason="Authentication required")
            return
        ticket = str(auth_message.get("ticket", ""))
        async with ROOMS_LOCK:
            room = ROOMS.get(code)
            if room is None or _room_is_expired(room):
                await websocket.close(code=1008, reason="Room not found or expired")
                return
            ticket_data = room["tickets"].get(ticket)
            if not ticket_data or ticket_data["expires_at"] < time.time():
                room["tickets"].pop(ticket, None)
                await websocket.close(code=1008, reason="Room ticket is invalid or expired")
                return
            uid = ticket_data["uid"]
            if uid in room["participants"]:
                room["tickets"].pop(ticket, None)
                await websocket.close(code=1008, reason="This account is already in the room")
                return
            if len(room["participants"]) >= 2:
                room["tickets"].pop(ticket, None)
                await websocket.close(code=1008, reason="This room already has two participants")
                return
            room["tickets"].pop(ticket, None)
            role = "A" if not room["participants"] else "B"
            room["participants"][uid] = {"websocket": websocket, "role": role}
            peer_present = len(room["participants"]) == 2

        await websocket.send_json({
            "type": "joined",
            "role": role,
            "peer_present": peer_present,
            "participant_count": 2 if peer_present else 1,
        })
        if peer_present:
            async with ROOMS_LOCK:
                room = ROOMS.get(code)
                if room:
                    await _send_peer_event(room, uid, {"type": "peer_joined"})

        while True:
            raw = await websocket.receive_text()
            if len(raw.encode("utf-8")) > MAX_SIGNAL_BYTES:
                await websocket.close(code=1009, reason="Signalling message too large")
                return
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.close(code=1003, reason="Invalid signalling message")
                return
            if not isinstance(message, dict) or message.get("type") not in {"offer", "answer", "ice", "hangup", "heartbeat"}:
                await websocket.close(code=1008, reason="Unsupported signalling message")
                return
            if message["type"] == "heartbeat":
                continue
            async with ROOMS_LOCK:
                room = ROOMS.get(code)
                if room and uid in room["participants"]:
                    await _send_peer_event(room, uid, {
                        "type": message["type"],
                        "payload": message.get("payload"),
                    })
    except asyncio.TimeoutError:
        await websocket.close(code=1008, reason="Authentication timed out")
    except WebSocketDisconnect:
        pass
    except Exception:
        # Log server-side diagnostics without logging tickets, SDP, or audio.
        logger.exception("Conversation signalling failed")
    finally:
        if uid:
            async with ROOMS_LOCK:
                room = ROOMS.get(code)
                if room:
                    room["participants"].pop(uid, None)
                    if room["participants"]:
                        try:
                            await _send_peer_event(room, uid, {"type": "peer_left"})
                        except Exception:
                            pass
                    else:
                        ROOMS.pop(code, None)
