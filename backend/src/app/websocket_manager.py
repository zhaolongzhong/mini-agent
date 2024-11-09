import logging
from typing import Union

from fastapi import WebSocket, WebSocketDisconnect

from app import schemas
from app.schemas.event_message import (
    EventMessage,
    EventMessageType,
    MessageEventPayload,
    MessageChunkEventPayload,
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # connection_id: WebSocket
        self.active_connections: dict[str, WebSocket] = {}
        # user_id: connection_id (websocket_request_id)
        self.user_connections: dict[str, set[str]] = {}

    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str):
        self.active_connections[connection_id] = websocket
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        logger.info(f"connected client: {connection_id}, total: {len(self.active_connections)}")

    async def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            user_id = next(
                (uid for uid, conns in self.user_connections.items() if connection_id in conns),
                None,
            )
            if user_id:
                self.user_connections[user_id].remove(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            websocket = self.active_connections.pop(connection_id, None)
            if websocket and not websocket.client_state.DISCONNECTED:
                try:
                    await websocket.close()
                except Exception as e:
                    logger.error(f"Error closing websocket: {e}, {websocket.client_state}")
            logger.info(f"disconnected client: {connection_id}, total: {len(self.active_connections)}")

    async def broadcast_event(
        self,
        event_message: EventMessage,
        user_id: str,
        websocket_request_id: str,
    ):
        if user_id not in self.user_connections:
            return
        connections = list(self.user_connections[user_id])
        connections_to_remove = []
        for connection_id in connections:
            if websocket_request_id and connection_id != websocket_request_id:
                continue
            connection = self.active_connections.get(connection_id)
            if connection:
                try:
                    event_text = event_message.model_dump_json()
                    if event_message.type != EventMessageType.PONG:
                        logger.debug(
                            f"broadcast_event, sender: {user_id}, event: {event_message.model_dump(exclude_none=True)}"
                        )
                    await connection.send_text(event_text)
                except WebSocketDisconnect:
                    connections_to_remove.append(connection_id)
                except RuntimeError as e:
                    if "websocket.send" in str(e) and "websocket.close" in str(e):
                        connections_to_remove.append(connection_id)
                        logger.warning(f"WebSocket already closed: {connection_id}")
                    else:
                        logger.error(f"RuntimeError sending message: {e}")
                        connections_to_remove.append(connection_id)
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
                    connections_to_remove.append(connection_id)

        for connection_id in connections_to_remove:
            await self.disconnect(connection_id)

    async def broadcast(
        self,
        user_id: str,
        websocket_request_id: str,
        event_content: Union[schemas.Message, schemas.MessageChunk, schemas.Conversation] | None,
    ):
        if event_content is None:
            logger.error("broadcast content is None")
            return

        try:
            if isinstance(event_content, schemas.Message):
                event_type = EventMessageType.MESSAGE
                payload = MessageEventPayload(json_dict=event_content.model_dump())
            elif isinstance(event_content, schemas.MessageChunk):
                event_type = EventMessageType.MESSAGE_CHUNK
                payload = MessageChunkEventPayload(json_dict=event_content.model_dump())
            else:
                logger.error(f"Unsupported content type: {type(event_content)}")
                return

            event_message = EventMessage(
                type=event_type,
                payload=payload,
                user_id=user_id,
            )
            await self.broadcast_event(
                event_message,
                user_id=user_id,
                websocket_request_id=websocket_request_id,
            )
        except Exception as e:
            logger.error(f"broadcast error: {e}")
