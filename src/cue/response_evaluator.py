"""Response evaluation module for self-improvement capabilities."""
import logging
from dataclasses import dataclass
from typing import Optional

from .schemas import CompletionResponse, RunMetadata

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of a response evaluation."""
    should_continue: bool
    reason: str
    suggested_prompt: Optional[str] = None


class ResponseEvaluator:
    """Evaluates agent responses for self-improvement."""

    def __init__(self, max_depth: int = 3):
        """Initialize the evaluator.
        
        Args:
            max_depth: Maximum number of consecutive evaluations allowed.
        """
        self.max_depth = max_depth
        self.evaluation_depth = 0
        
    def reset(self):
        """Reset evaluation depth counter."""
        self.evaluation_depth = 0

    async def evaluate_response(
        self,
        response: CompletionResponse,
        run_metadata: RunMetadata,
    ) -> EvaluationResult:
        """Evaluate if the agent should continue thinking about the response.
        
        Args:
            response: The response to evaluate
            run_metadata: Current run metadata
            
        Returns:
            EvaluationResult indicating if thinking should continue
        """
        if self.evaluation_depth >= self.max_depth:
            logger.debug(f"Max evaluation depth {self.max_depth} reached")
            return EvaluationResult(
                should_continue=False,
                reason="Maximum evaluation depth reached"
            )

        self.evaluation_depth += 1
        
        # Extract response text for evaluation
        response_text = response.text
        
        # Basic evaluation criteria
        evaluation_results = {
            "is_complete": self._evaluate_completeness(response_text),
            "has_action_items": self._evaluate_action_items(response_text),
            "could_use_tools": self._evaluate_tool_opportunities(response_text),
        }
        
        # Determine if should continue based on evaluation results
        should_continue = any(
            not result["satisfied"] for result in evaluation_results.values()
        )
        
        if should_continue:
            reason = self._generate_continuation_reason(evaluation_results)
            suggested_prompt = self._generate_follow_up_prompt(
                response_text, evaluation_results
            )
        else:
            self.reset()  # Reset depth counter for next chain
            reason = "Response meets evaluation criteria"
            suggested_prompt = None
            
        return EvaluationResult(
            should_continue=should_continue,
            reason=reason,
            suggested_prompt=suggested_prompt
        )

    def _evaluate_completeness(self, response_text: str) -> dict:
        """Check if the response seems complete.
        
        Basic checks for:
        - Proper conclusion
        - No trailing thoughts
        - Clear next steps if any
        """
        # Basic completeness checks
        has_conclusion = any(
            marker in response_text.lower() 
            for marker in ["therefore", "in conclusion", "finally"]
        )
        
        has_trailing_questions = "?" in response_text.split(".")[-1]
        
        return {
            "satisfied": has_conclusion and not has_trailing_questions,
            "reason": "Response lacks clear conclusion" if not has_conclusion
                     else "Has trailing questions" if has_trailing_questions
                     else "Complete"
        }

    def _evaluate_action_items(self, response_text: str) -> dict:
        """Check if there are incomplete action items.
        
        Looks for:
        - TODO items
        - Questions to be answered
        - Explicit next steps
        """
        action_markers = ["todo", "next steps", "should", "could", "would"]
        has_actions = any(
            marker in response_text.lower() 
            for marker in action_markers
        )
        
        return {
            "satisfied": not has_actions,  # If has actions, not satisfied
            "reason": "Has pending action items" if has_actions else "No pending actions"
        }

    def _evaluate_tool_opportunities(self, response_text: str) -> dict:
        """Check for potential tool usage opportunities.
        
        Looks for:
        - File operations mentioned without tool use
        - Search intentions without browse tool
        - Code discussions without analysis tools
        """
        tool_triggers = {
            "file": ["file", "directory", "folder", "path"],
            "search": ["search", "look up", "find out"],
            "code": ["code", "implementation", "function"]
        }
        
        missed_tools = []
        for tool, triggers in tool_triggers.items():
            if any(trigger in response_text.lower() for trigger in triggers):
                missed_tools.append(tool)
                
        return {
            "satisfied": len(missed_tools) == 0,
            "reason": f"Could use tools: {', '.join(missed_tools)}" if missed_tools
                     else "No missed tool opportunities"
        }

    def _generate_continuation_reason(self, evaluation_results: dict) -> str:
        """Generate a human-readable reason for continuation."""
        reasons = []
        for check, result in evaluation_results.items():
            if not result["satisfied"]:
                reasons.append(f"{check}: {result['reason']}")
        
        return " | ".join(reasons)

    def _generate_follow_up_prompt(
        self,
        response_text: str,
        evaluation_results: dict
    ) -> str:
        """Generate a prompt for follow-up thinking.
        
        Creates a context-aware prompt based on evaluation results.
        """
        prompts = []
        
        # Add relevant follow-up questions based on evaluation
        if not evaluation_results["is_complete"]["satisfied"]:
            prompts.append(
                "Can you provide a clear conclusion or summary of your thoughts?"
            )
            
        if not evaluation_results["has_action_items"]["satisfied"]:
            prompts.append(
                "There seem to be pending actions. Should we address these now?"
            )
            
        if not evaluation_results["could_use_tools"]["satisfied"]:
            prompts.append(
                "Consider if using available tools would help accomplish these tasks more effectively."
            )
            
        if prompts:
            return (
                "Let's improve this response further:\n" + 
                "\n".join(f"- {prompt}" for prompt in prompts)
            )
            
        return "Please review and enhance your previous response."