import json
import logging
from pathlib import Path
from typing import Optional

from typing_extensions import Callable

from .llm.llm_model import ChatModel
from .tools import (
    Tool,
    browse_web,
    # call_agent,
    execute_shell_command,
    make_plan,
    manage_drive,
    manage_email,
    read_file,
    run_python_script,
    scan_folder,
    write_to_file,
)
from .utils.function_to_json import function_to_json

logger = logging.getLogger(__name__)

_tag = "[ToolManager]"


class ToolManager:
    def __init__(self, tools_dir: Optional[Path] = None, definitions_dir: Optional[Path] = None):
        self.tools_dir = tools_dir or Path(__file__).parent / "tools"
        self.definitions_dir = definitions_dir or Path(__file__).parent / "tools"
        self.tools = {
            Tool.FileRead.value: read_file,
            Tool.FileWrite.value: write_to_file,
            # Tool.CallAgent.value: call_agent,
            Tool.CheckFolder.value: scan_folder,
            Tool.CodeInterpreter.value: run_python_script,
            Tool.ShellTool.value: execute_shell_command,
            Tool.MakePlan.value: make_plan,
            Tool.BrowseWeb.value: browse_web,
            Tool.ManageEmail.value: manage_email,
            Tool.ManageDrive.value: manage_drive,
        }

    def _get_tool_definition(self, tool_name: str, model: ChatModel = ChatModel.GPT_4O) -> Optional[dict]:
        """Load the JSON configuration for a specific tool from its respective file."""
        definition_path = self.definitions_dir / f"{tool_name}.json"

        if not definition_path.exists():
            logger.error(f"{_tag} Definition file for {tool_name} does not exist at {definition_path.resolve()}")
            return None

        try:
            with definition_path.open("r", encoding="utf-8") as file:
                function_definition_json = json.load(file)
        except json.JSONDecodeError as e:
            logger.error(f"{_tag} Invalid JSON in {definition_path}: {e}")
            return None

        model_id = model.model_id.lower()

        if "claude" in model_id:
            function_data = function_definition_json.get("function")
            if function_data:
                return {
                    "name": function_data.get("name"),
                    "description": function_data.get("description"),
                    "input_schema": function_data.get("parameters"),
                }

        return function_definition_json

    def get_tool_definitions(self, model: ChatModel, tools: Optional[list[Tool]] = None) -> list[dict]:
        """Iterate through the tools and gather their JSON configurations."""
        tools_configs = []
        if tools is None or len(tools) == 0:
            logger.debug(f"{_tag} No tools selected for definition retrieval.")
            return tools_configs

        for tool in tools:
            if isinstance(tool, Tool):
                config = self._get_tool_definition(tool.value, model)
            elif isinstance(tool, Callable):
                config = function_to_json(tool)
            if config:
                tools_configs.append(config)
        return tools_configs
