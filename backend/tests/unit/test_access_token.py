import pytest

from src.app.api.deps import validate_token
from src.app.core.config import get_settings
from tests.client_wrapper import ClientWrapper


@pytest.mark.unit
@pytest.mark.anyio
async def test_user_access_token():
    client = ClientWrapper(
        client_id="test_client",
        user_id="default_user_id",
        auto_connect=False,
    )

    client.login()
    token_data = await validate_token(client.access_token, get_settings())
    assert token_data.user_id == "default_user_id"
    assert not token_data.assistant_id


@pytest.mark.unit
@pytest.mark.anyio
async def test_assistant_access_token():
    client = ClientWrapper(
        client_id="test_client",
        user_id="default_user_id",
        assistant_id="default_assistant_id",
        auto_connect=False,
    )

    client.login()
    token_data = await validate_token(client.access_token, get_settings())
    assert token_data.user_id == "default_user_id"
    assert token_data.assistant_id == "default_assistant_id"
