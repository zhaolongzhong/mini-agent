import json
import logging

from fastapi import (
    Depends,
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)

from .. import deps
from ...websocket_manager import ConnectionManager
from ...schemas.event_message import (
    EventMessage,
    EventMessageType,
    PingPoingEventPayload,
    ClientConnectEventPayload,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    connection_manager: ConnectionManager = Depends(deps.get_connection_manager),
):
    await websocket.accept()
    websocket_request_id = websocket.query_params.get("websocket_request_id")
    connection_id = websocket_request_id or client_id
    logger.info(f"Client {connection_id} connecting, websocket_request_id: {websocket_request_id}")

    await connection_manager.connect(
        websocket=websocket,
        connection_id=connection_id,
        user_id="default_user_id",
    )

    # Send connection confirmation
    await handle_connection(
        connection_manager=connection_manager,
        client_id=client_id,
        user_id="default_user_id",
        websocket_request_id=websocket_request_id,
        payload=ClientConnectEventPayload(
            client_id=client_id, connection_id=connection_id, message="Connected successfully"
        ),
    )

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            event_type = EventMessageType(message_data.get("type"))

            if event_type in (EventMessageType.PING, EventMessageType.PONG):
                response_type = EventMessageType.PONG if event_type == EventMessageType.PING else EventMessageType.PING
                event_message = EventMessage(
                    type=response_type, payload=PingPoingEventPayload(type=response_type.value), client_id=client_id
                )
            else:
                event_message = EventMessage(
                    **message_data,
                )
                event_message.client_id = client_id

            await connection_manager.broadcast_event(
                event_message=event_message,
                user_id="default_user_id",
                websocket_request_id=websocket_request_id,
            )

    except WebSocketDisconnect:
        await handle_connection(
            connection_manager=connection_manager,
            client_id=client_id,
            user_id="default_user_id",
            websocket_request_id=websocket_request_id,
            type=EventMessageType.CLIENT_LEAVE,
            payload=ClientConnectEventPayload(
                client_id=client_id, connection_id=connection_id, message="WebSocket disconnected"
            ),
        )
    except Exception as e:
        logger.error(f"Error in websocket_endpoint: {e}")
        await handle_connection(
            connection_manager=connection_manager,
            client_id=client_id,
            user_id="default_user_id",
            websocket_request_id=websocket_request_id,
            type=EventMessageType.CLIENT_LEAVE,
            payload=ClientConnectEventPayload(client_id=client_id, connection_id=connection_id, message=str(e)),
        )


async def handle_connection(
    connection_manager: ConnectionManager,
    client_id: str,
    user_id: str,
    websocket_request_id: str,
    type: EventMessageType = EventMessageType.CLIENT_CONNECT,
    payload: ClientConnectEventPayload = None,
):
    event_message = EventMessage(
        type=type,
        payload=payload,
        client_id=client_id,
    )
    await connection_manager.broadcast_event(
        event_message=event_message,
        user_id=user_id,
        websocket_request_id=websocket_request_id,
    )
