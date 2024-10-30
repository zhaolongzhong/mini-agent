import logging
from uuid import uuid4
from typing import AsyncGenerator
from datetime import datetime

import pytest
import pytest_asyncio

from cue.schemas.message import Author, MessageCreate
from cue.memory.memory_service_client import MemoryServiceClient

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def memory_client() -> AsyncGenerator[MemoryServiceClient, None]:
    """Fixture to create and manage MemoryServiceClient instance."""
    client = MemoryServiceClient()
    await client.connect()
    try:
        yield client
    finally:
        await client.disconnect()


@pytest_asyncio.fixture
async def test_conversation(memory_client: MemoryServiceClient):
    """Fixture to create a test conversation and yield its object."""
    conversation = await memory_client.create_conversation(
        title=f"Test Conversation {uuid4()}", metadata={"test": True, "created_at": datetime.now().isoformat()}
    )
    try:
        yield conversation
    finally:
        try:
            await memory_client.delete_conversation(conversation.id)
        except Exception as e:
            logger.warning(f"Failed to delete test conversation: {e}")


@pytest.mark.integration
class TestMemoryServiceClient:
    @pytest.mark.asyncio
    async def test_create_message(self, memory_client: MemoryServiceClient, test_conversation) -> None:
        """Test creating a single message."""
        message_content = {"text": "Test message content"}
        conversation_id = test_conversation.id

        created_message = await memory_client.create_message(
            MessageCreate(
                conversation_id=conversation_id,
                author=Author(role="user"),
                content=message_content,
                metadata={"model": "gpt-4o"},
            )
        )

        assert created_message is not None, "Message should not be None"
        assert created_message.content.text == "Test message content", "Message content should match"
        assert created_message.conversation_id == conversation_id, "Conversation ID should match"
        assert created_message.author.role == "user", "Message role should be 'user'"
        assert created_message.metadata.model == "gpt-4o", "Message metadata should contain gpt-4o"
