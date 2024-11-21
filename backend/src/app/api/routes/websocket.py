import json
import logging
from typing import Optional

from fastapi import (
    Depends,
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)

from .. import deps
from ...core.config import get_settings
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
    user_id = await deps.authenticate_websocket_user(websocket, get_settings())
    if not user_id:
        await websocket.close(code=4001)
        return
    runner_id = websocket.query_params.get("runner_id", "").strip()

    await websocket.accept()

    session_id = None

    try:
        session_id = await connection_manager.connect(
            client_id=client_id,
            user_id=user_id,
            participant_id=runner_id if runner_id else user_id,
            websocket=websocket,
        )

        notification_recipient_ids = await connection_manager.get_participants(user_id)
        if session_id:
            await connection_manager.broadcast_connection_event(
                client_id=client_id,
                sender_id=runner_id if runner_id else user_id,
                recipients=list(notification_recipient_ids),
                is_connect=True,
            )
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                logger.info(f"Received message from '{user_id}' to '{message_data}")

                event_type = EventMessageType(message_data.get("type"))
                event_message = EventMessage(
                    **message_data,
                )
                recipient = event_message.payload.recipient if event_message.payload.recipient else user_id
                event_message = event_message.model_copy(
                    update={
                        "client_id": client_id,
                        "payload": event_message.payload.model_copy(
                            update={"user_id": user_id, "recipient": recipient}
                        ),
                    }
                )

                if event_type in (EventMessageType.PING, EventMessageType.PONG):
                    response = EventMessage(
                        client_id=client_id,
                        type=EventMessageType.PONG,
                        payload=PingPongEventPayload(type=EventMessageType.PONG),
                    )
                    await connection_manager.send_personal_message(response.model_dump_json(), session_id)
                elif event_type == EventMessageType.CLIENT_STATUS:
                    await connection_manager.send_message(message=event_message)
                elif event_type in (EventMessageType.USER, EventMessageType.ASSISTANT):
                    results = await connection_manager.send_message(message=event_message)
                    success = True
                    msg = ""
                    for status, error in results:
                        if not status:
                            success = False
                            msg += error

                    if not success:
                        logger.warning(f"Could not deliver message. {msg}")
                        offline_message = EventMessage(
                            client_id=client_id,
                            type=EventMessageType.GENERIC,
                            payload=ClientEventPayload(
                                client_id=client_id,
                                message=msg,
                            ),
                        )
                        await connection_manager.send_personal_message(
                            offline_message.model_dump_json(),
                            session_id,
                        )
                        continue

                else:
                    await connection_manager.send_message(message=event_message)

            except json.JSONDecodeError:
                error_message = json.dumps({"system": True, "message": "Invalid message format. Please send JSON."})
                await connection_manager.send_personal_message(error_message, session_id)
                logger.warning(f"Invalid JSON received from '{user_id}'.")

            except Exception as e:
                error_message = json.dumps({"system": True, "message": f"Error processing message: {str(e)}"})
                await connection_manager.send_personal_message(error_message, session_id)
                logger.error(f"Error processing message from '{user_id}': {e}")

    except WebSocketDisconnect as e:
        logger.info(
            f"WebSocket disconnected for user '{user_id}' (code: {e.code}, reason: {e.reason}), session_id: {session_id}"
        )
        await handle_disconnect(
            connection_manager=connection_manager,
            client_id=client_id,
            session_id=session_id,
            user_id=user_id,
            runner_id=runner_id,
        )
    except Exception as e:
        logger.error(f"Unexpected error with WebSocket for user '{user_id}': {e}")
        await handle_disconnect(
            connection_manager=connection_manager,
            client_id=client_id,
            session_id=session_id,
            user_id=user_id,
            runner_id=runner_id,
        )


async def handle_disconnect(
    connection_manager: ConnectionManager,
    client_id: str,
    session_id: str,
    user_id: str,
    runner_id: Optional[str] = None,
) -> None:
    notification_recipient_ids = await connection_manager.disconnect(session_id=session_id)
    await connection_manager.broadcast_connection_event(
        client_id=client_id,
        sender_id=runner_id if runner_id else user_id,
        recipients=notification_recipient_ids,
        is_connect=False,
    )
