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
    ClientEventPayload,
    PingPongEventPayload,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    connection_manager: ConnectionManager = Depends(deps.get_connection_manager),
):
    user_id = websocket.query_params.get("user_id")
    if not user_id:
        user_id = client_id

    await websocket.accept()
    session_id = await connection_manager.connect(user_id, websocket)

    # Send back connect confirmation
    event_message = EventMessage(
        type=EventMessageType.CLIENT_CONNECT,
        client_id=client_id,
        payload=ClientEventPayload(client_id=client_id, session_id=session_id, message="Connected successfully"),
    )
    event_text = event_message.model_dump_json()
    await connection_manager.send_personal_message(event_text, session_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                logger.info(f"Received message from '{user_id}' to '{message_data}")

                event_type = EventMessageType(message_data.get("type"))
                event_message = EventMessage(
                    **message_data,
                )
                event_message.client_id = client_id

                if event_type in (EventMessageType.PING, EventMessageType.PONG):
                    response = EventMessage(
                        client_id=client_id,
                        type=EventMessageType.PONG,
                        payload=PingPongEventPayload(type=EventMessageType.PONG),
                    )
                    await connection_manager.send_personal_message(response.model_dump_json(), session_id)
                elif event_type in (EventMessageType.USER, EventMessageType.ASSISTANT):
                    event_message.client_id = client_id
                    recipient_id = event_message.payload.recipient
                    recipient_sessions = await connection_manager.get_user_sessions(recipient_id)
                    if not recipient_sessions:
                        # Optionally, send a message back to the sender indicating the recipient is offline
                        offline_message = EventMessage(
                            client_id=client_id,
                            type=EventMessageType.GENERIC,
                            payload=ClientEventPayload(
                                client_id=client_id,
                                session_id=session_id,
                                message=f"User '{recipient_id}' is offline.",
                            ),
                        )
                        await connection_manager.send_personal_message(offline_message.model_dump_json(), session_id)
                        logger.warning(f"User '{recipient_id}' is offline. Could not deliver message.")
                        continue

                    # Send the message to all active sessions of the recipient
                    event_message.payload.sender = user_id
                    event_text = event_message.model_dump_json()
                    for recipient_session_id in recipient_sessions:
                        await connection_manager.send_personal_message(
                            message=event_text, session_id=recipient_session_id
                        )

                else:
                    event_message = EventMessage(
                        **message_data,
                    )

            except json.JSONDecodeError:
                error_message = json.dumps({"system": True, "message": "Invalid message format. Please send JSON."})
                await connection_manager.send_personal_message(error_message, session_id)
                logger.warning(f"Invalid JSON received from '{user_id}'.")

            except Exception as e:
                error_message = json.dumps({"system": True, "message": f"Error processing message: {str(e)}"})
                await connection_manager.send_personal_message(error_message, session_id)
                logger.error(f"Error processing message from '{user_id}': {e}")

    except WebSocketDisconnect as e:
        logger.info(f"WebSocket disconnected for user '{user_id}' (code: {e.code}, reason: {e.reason})")
        await connection_manager.disconnect(session_id)

    except Exception as e:
        logger.error(f"Unexpected error with WebSocket for user '{user_id}': {e}")
        await connection_manager.disconnect(session_id)
