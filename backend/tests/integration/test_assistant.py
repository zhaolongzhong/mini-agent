import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.anyio
async def test_create_assistant(async_client: AsyncClient):
    assistant_data = {
        "name": f"test_assistant_{uuid.uuid4().hex[:8]}",
        "metadata": {"is_primary": True},
    }

    response = await async_client.post("/api/v1/assistants", json=assistant_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == assistant_data["name"].lower()
    assert data["metadata"]["is_primary"] == assistant_data["metadata"]["is_primary"]
