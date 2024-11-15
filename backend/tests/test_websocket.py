import json
import uuid

import pytest
from websockets.client import connect

from src.app.schemas.event_message import (
    EventMessage,
    EventMessageType,
    PingPongEventPayload,
    GenericMessagePayload,
    CompletionMessagePayload,
)


@pytest.mark.unit
@pytest.mark.anyio
async def test_websocket_connection():
    client_id = str(uuid.uuid4())
    user_id = "test_user"

    async with connect(f"ws://localhost:8000/api/v1/ws/{client_id}?user_id={user_id}") as websocket:
        # Receive connection confirmation
        response = await websocket.recv()
        response_data = json.loads(response)

        assert response_data["type"] == EventMessageType.CLIENT_CONNECT
        assert response_data["client_id"] == client_id
        assert "session_id" in response_data["payload"]
        assert response_data["payload"]["message"] == "Connected successfully"


@pytest.mark.unit
@pytest.mark.anyio
async def test_websocket_ping_pong():
    client_id = str(uuid.uuid4())
    user_id = "test_user"

    async with connect(f"ws://localhost:8000/api/v1/ws/{client_id}?user_id={user_id}") as websocket:
        # Wait for connection confirmation
        await websocket.recv()

        # Send PING
        ping_message = EventMessage(
            client_id=client_id, type=EventMessageType.PING, payload=PingPongEventPayload(type="PING")
        )
        await websocket.send(ping_message.model_dump_json())

        # Receive PONG
        response = await websocket.recv()
        response_data = json.loads(response)

        assert response_data["type"] == EventMessageType.PONG
        assert response_data["client_id"] == client_id
        assert response_data["payload"]["type"] == EventMessageType.PONG


@pytest.mark.unit
@pytest.mark.anyio
async def test_two_users_messaging():
    # Setup first user
    client_id_1 = str(uuid.uuid4())
    user_id_1 = "test_user_1"

    # Setup second user
    client_id_2 = str(uuid.uuid4())
    user_id_2 = "test_user_2"

    async with connect(f"ws://localhost:8000/api/v1/ws/{client_id_1}?user_id={user_id_1}") as websocket1:
        async with connect(f"ws://localhost:8000/api/v1/ws/{client_id_2}?user_id={user_id_2}") as websocket2:
            # Wait for connection confirmations
            await websocket1.recv()
            await websocket2.recv()

            # User 1 sends message to User 2
            message_1_to_2 = EventMessage(
                client_id=client_id_1,
                type=EventMessageType.USER,
                payload=GenericMessagePayload(message="Hello from user 1!", recipient=user_id_2),
            )
            await websocket1.send(message_1_to_2.model_dump_json())

            # User 2 should receive the message
            response_2 = await websocket2.recv()
            response_data_2 = json.loads(response_2)

            assert response_data_2["type"] == EventMessageType.USER
            assert response_data_2["payload"]["message"] == "Hello from user 1!"
            assert response_data_2["payload"]["sender"] == user_id_1

            # User 2 sends reply to User 1
            message_2_to_1 = EventMessage(
                client_id=client_id_2,
                type=EventMessageType.USER,
                payload=GenericMessagePayload(message="Hello back from user 2!", recipient=user_id_1),
            )
            await websocket2.send(message_2_to_1.model_dump_json())

            # User 1 should receive the reply
            response_1 = await websocket1.recv()
            response_data_1 = json.loads(response_1)

            assert response_data_1["type"] == EventMessageType.USER
            assert response_data_1["payload"]["message"] == "Hello back from user 2!"
            assert response_data_1["payload"]["sender"] == user_id_2


@pytest.mark.unit
@pytest.mark.anyio
async def test_user_assistant_chat_conversation():
    # Setup human user
    user_client_id = str(uuid.uuid4())
    user_id = "test_human_user"

    # Setup AI assistant
    assistant_client_id = str(uuid.uuid4())
    assistant_id = "test_ai_assistant"

    async with connect(f"ws://localhost:8000/api/v1/ws/{user_client_id}?user_id={user_id}") as user_websocket:
        async with connect(
            f"ws://localhost:8000/api/v1/ws/{assistant_client_id}?user_id={assistant_id}"
        ) as assistant_websocket:
            # Wait for both connections to be established
            await user_websocket.recv()
            await assistant_websocket.recv()

            # Human user sends a message to AI assistant
            user_message = EventMessage(
                client_id=user_client_id,
                type=EventMessageType.USER,
                payload=CompletionMessagePayload(
                    role="user", content="Can you help me with a question?", recipient=assistant_id
                ),
            )
            await user_websocket.send(user_message.model_dump_json())

            # Verify assistant receives the user's message
            assistant_received = await assistant_websocket.recv()
            assistant_received_data = json.loads(assistant_received)

            assert assistant_received_data["type"] == EventMessageType.USER
            assert assistant_received_data["payload"]["content"] == "Can you help me with a question?"
            assert assistant_received_data["payload"]["sender"] == user_id

            # AI assistant sends response back to human user
            assistant_response = EventMessage(
                client_id=assistant_client_id,
                type=EventMessageType.ASSISTANT,
                payload=CompletionMessagePayload(
                    role="assistant", content="Of course! What would you like to know?", recipient=user_id
                ),
            )
            await assistant_websocket.send(assistant_response.model_dump_json())

            # Verify user receives the assistant's response
            user_received = await user_websocket.recv()
            user_received_data = json.loads(user_received)

            assert user_received_data["type"] == EventMessageType.ASSISTANT
            assert user_received_data["payload"]["content"] == "Of course! What would you like to know?"
            assert user_received_data["payload"]["sender"] == assistant_id


@pytest.mark.unit
@pytest.mark.anyio
async def test_message_to_offline_user():
    # Setup online user
    client_id_online = str(uuid.uuid4())
    user_id_online = "test_user_online"
    user_id_offline = "test_user_offline"

    async with connect(f"ws://localhost:8000/api/v1/ws/{client_id_online}?user_id={user_id_online}") as websocket:
        # Wait for connection confirmation
        await websocket.recv()

        # Send message to offline user
        message = EventMessage(
            client_id=client_id_online,
            type=EventMessageType.USER,
            payload=CompletionMessagePayload(role="user", content="Hello offline user!", recipient=user_id_offline),
        )
        await websocket.send(message.model_dump_json())

        # Should receive offline notification (generic)
        response = await websocket.recv()
        response_data = json.loads(response)

        assert response_data["type"] == EventMessageType.GENERIC
        assert "offline" in response_data["payload"]["message"].lower()
