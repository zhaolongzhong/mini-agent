from typing import Literal, ClassVar

from .base import BaseTool, ToolResult
from .system_management import SystemManagement
from ..tools.utils.function_utils import get_definition_by_model


class RestartTool(BaseTool):
    """
    A tool that allows the system to restart the system when encountering unrecoverable errors
    or when testing changes. This tool provides a safe way to perform system restarts with
    proper logging and error handling.
    """

    name: ClassVar[Literal["restart"]] = "restart"

    def __init__(self):
        self._function = self.restart
        super().__init__()
        self.system_management = SystemManagement()

    def to_json(self, model: str = "", use_file_definition: bool = True) -> dict:
        """
        Generate the JSON schema for the restart tool.

        Args:
            model (str): The model identifier to customize the schema for specific models.
            use_file_definition (bool): Whether to use file-based definition.

        Returns:
            dict: The JSON schema definition for the restart tool.
        """
        definition = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": (
                    "Initiates a system restart when encountering an unrecoverable error "
                    "or when testing system changes. Requires a valid reason for audit purposes."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "The specific reason and context for requesting a system restart.",
                        }
                    },
                    "required": ["reason"],
                    "additionalProperties": False,
                },
            },
        }
        return get_definition_by_model(definition, model)

    async def __call__(self, reason: str, **kwargs) -> ToolResult:
        """
        Callable interface for the restart tool.

        Args:
            reason (str): The reason for the restart request.
            **kwargs: Additional keyword arguments (ignored).

        Returns:
            ToolResult: The result of the restart operation.
        """
        return await self.restart(reason)

    async def restart(self, reason: str) -> ToolResult:
        """
        Initiates a system restart with the provided reason.

        Args:
            reason (str): The reason for the restart request.

        Returns:
            ToolResult: Success or error message from the restart attempt.
        """
        if not reason or not reason.strip():
            return ToolResult(error="Restart reason cannot be empty or whitespace only")

        try:
            await self.system_management.request_restart(reason.strip())
            return ToolResult(output=f"Successfully initiated restart request. Reason: {reason}")
        except Exception as error:
            return ToolResult(error=f"Failed to initiate system restart: {str(error)}")
