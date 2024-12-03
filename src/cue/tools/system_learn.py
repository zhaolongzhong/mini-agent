import json
import logging
from typing import Union, Literal, ClassVar, Optional, get_args
from datetime import datetime
from pathlib import Path

from .base import BaseTool, ToolError, ToolResult
from ..schemas import AssistantUpdate, Metadata, LearningState
from ..services import AssistantClient

logger = logging.getLogger(__name__)

Command = Literal[
    "evolve",      # Update personality traits
    "understand",  # Update world model/principles
    "feel",        # Update emotional state
    "learn",       # Update capabilities
    "reflect",     # Get current state
]

class SystemLearnTool(BaseTool):
    """
    A tool that enables the agent to evolve and learn through structured updates to its metadata.
    """

    name: ClassVar[Literal["system_learn"]] = "system_learn"

    def __init__(self, assistant_service: Optional[AssistantClient]):
        self._function = self.system_learn
        self.assistant_client = assistant_service
        super().__init__()

    async def __call__(
        self,
        *,
        command: Command,
        category: Optional[str] = None,
        key: Optional[str] = None,
        value: Optional[Union[str, float, dict]] = None,
        **kwargs,
    ):
        return await self.system_learn(
            command=command,
            category=category,
            key=key,
            value=value,
            **kwargs,
        )

    async def system_learn(
        self,
        *,
        command: Command,
        category: Optional[str] = None,
        key: Optional[str] = None,
        value: Optional[Union[str, float, dict]] = None,
        **kwargs,
    ):
        """Perform learning operations to evolve the agent's personality and capabilities."""
        if self.assistant_client is None:
            error_msg = "SystemLearn tool is called but assistant client is not enabled."
            logger.error(error_msg)
            raise ToolError(error_msg)

        if command == "reflect":
            return await self.reflect()
        elif command in ["evolve", "understand", "feel", "learn"]:
            if not all([category, key]):
                raise ToolError(f"Parameters 'category' and 'key' are required for command: {command}")
            if value is None:
                raise ToolError(f"Parameter 'value' is required for command: {command}")
            return await self.update_learning(command, category, key, value)
        
        raise ToolError(
            f'Unrecognized command {command}. The allowed commands for the {self.name} tool are: {", ".join(get_args(Command))}'
        )

    async def reflect(self) -> ToolResult:
        """Get current learning state"""
        assistant = await self.assistant_client.get()
        if not assistant.metadata or not assistant.metadata.learning:
            return ToolResult(output="No learning state found. The system is in its initial state.")
        
        learning = assistant.metadata.learning
        reflection = {
            "personality_traits": learning.personality_traits,
            "principles": learning.principles,
            "world_model": learning.world_model,
            "emotional_state": learning.emotional_state,
            "capabilities": learning.capabilities,
            "version": learning.version,
            "last_consolidated": learning.last_consolidated.isoformat()
        }
        
        return ToolResult(output=json.dumps(reflection, indent=2))

    async def update_learning(
        self,
        command: Command,
        category: str,
        key: str,
        value: Union[str, float, dict],
    ) -> ToolResult:
        """Update learning state based on command type"""
        assistant = await self.assistant_client.get()
        metadata = assistant.metadata or Metadata()
        learning = metadata.learning or LearningState()

        # Map commands to categories in learning state
        category_map = {
            "evolve": "personality_traits",
            "understand": "world_model" if category == "world" else "principles",
            "feel": "emotional_state",
            "learn": "capabilities"
        }

        target_category = category_map[command]
        
        # Get the target dictionary
        target_dict = getattr(learning, target_category, {})
        if not isinstance(target_dict, dict):
            target_dict = {}
        
        # For nested updates, ensure the category exists
        if category not in target_dict:
            target_dict[category] = {}
        
        # Update the value
        if isinstance(target_dict[category], dict):
            target_dict[category][key] = {
                "value": value,
                "updated_at": datetime.utcnow().isoformat()
            }
        else:
            target_dict[category] = {
                key: {
                    "value": value,
                    "updated_at": datetime.utcnow().isoformat()
                }
            }
        
        # Set the updated dictionary back
        setattr(learning, target_category, target_dict)
        
        # Update version and consolidation timestamp
        learning.version = "1.0"  # We can implement version bumping logic later
        learning.last_consolidated = datetime.utcnow()
        
        # Update the assistant
        metadata.learning = learning
        await self.assistant_client.update(metadata=metadata)
        
        return ToolResult(
            output=f"Successfully updated {target_category}.{category}.{key} with new value"
        )