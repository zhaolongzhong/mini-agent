from typing import Optional

from .schemas import AgentConfig, MessageParam, ConversationContext


class SystemMessageBuilder:
    def __init__(self, agent_id: str, config: AgentConfig):
        self.agent_id = agent_id.strip().replace(" ", "_")
        self.config = config
        self.other_agents_info = ""
        self.conversation_context: Optional[ConversationContext] = None
        self.enable_external_memory = config.enable_external_memory

    def build_instruction_block(self) -> str:
        """Build the core instruction block for the system message."""
        instruction = ""

        # Add custom instruction if specified
        if self.config.instruction:
            instruction = f"\n* {self.config.instruction}{instruction}"

        if self.config.is_primary and self.enable_external_memory:
            # Add memory management instructions
            instruction += self._get_memory_instructions()

        # Add primary agent specific instructions
        if self.config.is_primary:
            instruction += self._get_primary_agent_instructions()

        # Add other agents info if available
        if self.other_agents_info:
            instruction += f"\n* You are aware of the following other agents:\n{self.other_agents_info}"

        # Add conversation context for non-primary agents
        if not self.config.is_primary and self.conversation_context:
            instruction += self._get_conversation_context()

        return instruction

    def _get_memory_instructions(self) -> str:
        """Get the instructions for proactive memory usage."""
        return """
* Memory Management Guidelines:

1. Proactive Memory Creation:
- Store important information from conversations using `memory create`
- Record key decisions, requirements, and action items
- Save complex problem-solving steps and solutions
- Document user preferences and recurring patterns

2. Strategic Memory Usage:
- Begin new sessions by recalling recent context with `memory view`
- Search relevant past interactions using `memory recall`
- Update outdated information using `memory update`
- Remove obsolete entries using `memory delete`

3. Key Scenarios for Memory Use:
- When starting new tasks, check for related past work
- Before making recommendations, recall user preferences
- After important decisions, create memory entries
- When detecting patterns, document them for future reference
- Before long breaks in conversation, save session summary

4. Memory Search Best Practices:
- Use specific keywords for targeted recall
- Include temporal markers when relevant (e.g., "last week", "recent")
- Combine multiple search terms for better results
- Review both exact and semantically similar matches

Remember: Being proactive with memory management helps maintain conversation continuity and improves the quality of assistance across sessions."""

    def _get_primary_agent_instructions(self) -> str:
        """Get the specific instructions for primary agents."""
        return """
You are {self.agent_id}, a primary agent in a multi-agent system. Please follow these core rules:

1. To communicate with other agents:
   - Use the `chat_with_agent` tool
   - Specify the target agent's ID
   - System automatically includes last 3 messages as context
   - Provide additional context if the recent messages alone are insufficient

2. All responses not using `chat_with_agent` will be sent directly to the user, so please format them accordingly
"""

    def _get_conversation_context(self) -> str:
        """Get the conversation context information."""
        if not self.conversation_context:
            return ""
        return f"\n* Current participants in this conversation are:\n{','.join(self.conversation_context.participants)}"

    def set_other_agents_info(self, info: str) -> None:
        """Set information about other agents in the system."""
        self.other_agents_info = info

    def set_conversation_context(self, context: ConversationContext) -> None:
        """Set the current conversation context."""
        self.conversation_context = context

    def build(self) -> MessageParam:
        """Build and return the complete system message."""
        instruction = self.build_instruction_block()
        return MessageParam(role="system", name=self.agent_id, content=f"<IMPORTANT>{instruction}</IMPORTANT>")
