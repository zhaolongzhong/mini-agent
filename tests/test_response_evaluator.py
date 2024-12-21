"""Tests for the response evaluator module."""
import pytest
from cue.response_evaluator import ResponseEvaluator, EvaluationResult
from cue.schemas import CompletionResponse, RunMetadata


@pytest.fixture
def evaluator():
    return ResponseEvaluator()


@pytest.mark.asyncio
async def test_evaluate_incomplete_response(evaluator):
    response = CompletionResponse(
        text="I think we should look into this further but I'm not sure",
        role="assistant"
    )
    run_metadata = RunMetadata(tool_calls=[])
    
    result = await evaluator.evaluate_response(response, run_metadata)
    
    assert isinstance(result, EvaluationResult)
    assert result.should_continue is True
    assert "lacks clear conclusion" in result.reason.lower()
    assert result.suggested_prompt is not None


@pytest.mark.asyncio
async def test_evaluate_complete_response(evaluator):
    response = CompletionResponse(
        text="Therefore, based on the analysis, we should proceed with the implementation. " 
             "The next steps are clear and no further investigation is needed.",
        role="assistant"
    )
    run_metadata = RunMetadata(tool_calls=[])
    
    result = await evaluator.evaluate_response(response, run_metadata)
    
    assert isinstance(result, EvaluationResult)
    assert result.should_continue is False
    assert "complete" in result.reason.lower()
    assert result.suggested_prompt is None


@pytest.mark.asyncio
async def test_evaluate_response_with_missed_tools(evaluator):
    response = CompletionResponse(
        text="We should search through the files to find the implementation " 
             "and then look up the documentation.",
        role="assistant"
    )
    run_metadata = RunMetadata(tool_calls=[])
    
    result = await evaluator.evaluate_response(response, run_metadata)
    
    assert isinstance(result, EvaluationResult)
    assert result.should_continue is True
    assert any(tool in result.reason.lower() for tool in ["file", "search"])
    assert result.suggested_prompt is not None


@pytest.mark.asyncio
async def test_evaluate_response_with_pending_actions(evaluator):
    response = CompletionResponse(
        text="We should implement this feature. TODO: Add tests and documentation.",
        role="assistant"
    )
    run_metadata = RunMetadata(tool_calls=[])
    
    result = await evaluator.evaluate_response(response, run_metadata)
    
    assert isinstance(result, EvaluationResult)
    assert result.should_continue is True
    assert "pending action" in result.reason.lower()
    assert result.suggested_prompt is not None


@pytest.mark.asyncio
async def test_max_evaluation_depth(evaluator):
    response = CompletionResponse(
        text="We should look into this more.",
        role="assistant"
    )
    run_metadata = RunMetadata(tool_calls=[])
    
    # Force max depth
    evaluator.evaluation_depth = evaluator.max_depth
    
    result = await evaluator.evaluate_response(response, run_metadata)
    
    assert isinstance(result, EvaluationResult)
    assert result.should_continue is False
    assert "maximum evaluation depth" in result.reason.lower()
    assert result.suggested_prompt is None