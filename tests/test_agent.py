"""Tests for the Agent class."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from cue._agent import Agent
from cue.schemas import AgentConfig, CompletionResponse, RunMetadata, Author
from cue.tools import ToolManager


@pytest.fixture
def config():
    return AgentConfig(
        id="test_agent",
        model="gpt-4",
        api_key="test_key",
    )


@pytest.fixture
def agent(config):
    return Agent(config)


@pytest.fixture
def tool_manager():
    return MagicMock(spec=ToolManager)


@pytest.mark.asyncio
async def test_send_messages_with_response_evaluation(agent):
    # Mock the LLMClient
    agent.client.send_completion_request = AsyncMock()
    initial_response = CompletionResponse(
        text="I think we should look into this further",
        role="assistant"
    )
    improved_response = CompletionResponse(
        text="After analysis, we should proceed with implementation. Here are the concrete steps...",
        role="assistant"
    )
    agent.client.send_completion_request.side_effect = [initial_response, improved_response]
    
    # Create test messages and metadata
    messages = [{"role": "user", "content": "What should we do next?"}]
    run_metadata = RunMetadata(tool_calls=[])
    
    # Send messages
    response = await agent.send_messages(messages, run_metadata)
    
    # Verify that send_completion_request was called twice
    assert agent.client.send_completion_request.call_count == 2
    
    # Verify we got the improved response
    assert response == improved_response
    assert "concrete steps" in response.text


@pytest.mark.asyncio
async def test_send_messages_with_complete_response(agent):
    # Mock the LLMClient
    agent.client.send_completion_request = AsyncMock()
    complete_response = CompletionResponse(
        text="Therefore, based on the analysis, we should proceed with the implementation.",
        role="assistant"
    )
    agent.client.send_completion_request.return_value = complete_response
    
    # Create test messages and metadata
    messages = [{"role": "user", "content": "What should we do next?"}]
    run_metadata = RunMetadata(tool_calls=[])
    
    # Send messages
    response = await agent.send_messages(messages, run_metadata)
    
    # Verify that send_completion_request was called once
    agent.client.send_completion_request.assert_called_once()
    
    # Verify we got the complete response
    assert response == complete_response


@pytest.mark.asyncio
async def test_send_messages_respects_max_depth(agent):
    # Mock the LLMClient
    agent.client.send_completion_request = AsyncMock()
    incomplete_response = CompletionResponse(
        text="I think we should look into this",
        role="assistant"
    )
    agent.client.send_completion_request.return_value = incomplete_response
    
    # Force max depth in evaluator
    agent.response_evaluator.evaluation_depth = agent.response_evaluator.max_depth
    
    # Create test messages and metadata
    messages = [{"role": "user", "content": "What should we do next?"}]
    run_metadata = RunMetadata(tool_calls=[])
    
    # Send messages
    response = await agent.send_messages(messages, run_metadata)
    
    # Verify that send_completion_request was called only once due to max depth
    agent.client.send_completion_request.assert_called_once()
    
    # Verify we got the incomplete response
    assert response == incomplete_response