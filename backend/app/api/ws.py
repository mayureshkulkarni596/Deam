import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.db import SessionLocal
from app.models import User
from app.security import decode_access_token

router = APIRouter()

class WebSocketHub:
    def __init__(self):
        self.residents: dict[int, set[WebSocket]] = {}
    async def connect(self, user_id: int, socket: WebSocket):
        await socket.accept()
        self.residents.setdefault(user_id, set()).add(socket)
    def disconnect(self, user_id: int, socket: WebSocket):
        self.residents.get(user_id, set()).discard(socket)
    async def publish_resident(self, user_id: int, event_type: str, data: dict):
        event = {"type": event_type, "data": data, "ts": datetime.now(timezone.utc).isoformat()}
        for socket in list(self.residents.get(user_id, set())):
            try:
                await socket.send_json(event)
            except Exception:
                self.disconnect(user_id, socket)

hub = WebSocketHub()

@router.websocket("/ws/resident")
async def resident_socket(socket: WebSocket, token: str):
    try:
        claims = decode_access_token(token)
        user_id = int(claims["sub"])
        with SessionLocal() as db:
            user = db.get(User, user_id)
            if user is None or not user.is_active or user.role != "resident":
                await socket.close(code=1008)
                return
    except Exception:
        await socket.close(code=1008)
        return
    await hub.connect(user_id, socket)
    try:
        while True:
            try:
                await asyncio.wait_for(socket.receive_text(), timeout=20)
            except asyncio.TimeoutError:
                await socket.send_json({"type": "ping", "ts": datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect:
        hub.disconnect(user_id, socket)
