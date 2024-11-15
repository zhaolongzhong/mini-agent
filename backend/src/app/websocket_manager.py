import uuid
import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.active_users: dict[str, set[str]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> str:
        async with self.lock:
            session_id = str(uuid.uuid4())
            if user_id not in self.active_users:
                self.active_users[user_id] = set()
            self.active_users[user_id].add(session_id)
            self.active_connections[session_id] = websocket
            logger.info(f"User '{user_id}' connected with session_id '{session_id}'.")
            return session_id

    async def disconnect(self, session_id: str):
        async with self.lock:
            websocket = self.active_connections.pop(session_id, None)
            if websocket:
                try:
                    if not websocket.client_state.DISCONNECTED:
                        await websocket.close()
                except Exception as e:
                    logger.debug(f"Error while closing websocket: {e}")
            for user_id, sessions in self.active_users.items():
                if session_id in sessions:
                    sessions.remove(session_id)
                    logger.info(f"User '{user_id}' disconnected from session_id '{session_id}'.")
                    if not sessions:
                        del self.active_users[user_id]
                        logger.info(f"User '{user_id}' has no more active sessions.")
                    break

    async def send_personal_message(self, message: str, session_id: str):
        websocket = self.active_connections.get(session_id)
        if websocket:
            try:
                await websocket.send_text(message)
                logger.debug(f"Sent message to session_id '{session_id}': {message}")
            except Exception as e:
                logger.error(f"Error sending message to session_id '{session_id}': {e}")

    async def broadcast_message(self, message: str, user_id: str):
        async with self.lock:
            sessions = self.active_users.get(user_id, set()).copy()
        for session_id in sessions:
            await self.send_personal_message(message, session_id)

    async def get_user_sessions(self, user_id: str) -> set[str]:
        async with self.lock:
            return self.active_users.get(user_id, set()).copy()
