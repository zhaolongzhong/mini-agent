import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.anyio
async def test_create_conversation(async_client: AsyncClient):
    conversation_data = {
        "title": f"test_conversation_{uuid.uuid4().hex[:8]}",
        "metadata": {"test": "data"},
    }

    response = await async_client.post("/api/v1/conversations/", json=conversation_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == conversation_data["title"].lower()
    assert "id" in data
