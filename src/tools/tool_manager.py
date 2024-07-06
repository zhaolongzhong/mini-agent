import json
from enum import Enum
from pathlib import Path

from llm_client.llm_model import ChatModel
from tools.execute_shell_command import execute_shell_command
from tools.read_file import read_file
from tools.run_python_script import run_python_script
from tools.scan_folder import scan_folder
from tools.write_to_file import write_to_file
from utils.logs import logger

_tag = "[ToolManager]"


class Tool(Enum):
    FileRead = "read_file"
    FileWrite = "write_to_file"
    CheckFolder = "scan_folder"
    CodeInterpreter = "run_python_script"
    ShellTool = "execute_shell_command"


class ToolManager:
    def __init__(self):
        self.tools = {
            Tool.FileRead.value: read_file,
            Tool.FileWrite.value: write_to_file,
            Tool.CheckFolder.value: scan_folder,
            Tool.CodeInterpreter.value: run_python_script,
            Tool.ShellTool.value: execute_shell_command,
        }

        self.tools_path = Path(__file__).parent
        # logger.debug(f"{_tag} tools_path: {self.tools_path}")

    def get_tool_config(self, tool_name: str, model: ChatModel = ChatModel.GPT_4O) -> dict | None:
        """Load the JSON configuration for a specific tool from its respective file."""
        config_path = Path(self.tools_path) / f"{tool_name}.json"

        if not config_path.exists():
            logger.error(f"Configuration file for {tool_name} does not exist")
            return None

        with config_path.open("r", encoding="utf-8") as file:
            function_definition_json = json.load(file)

        model = model.name.lower()

        if "claude" in model:
            function_data = function_definition_json.get("function")
            if function_data:
                return {
                    "name": function_data.get("name"),
                    "description": function_data.get("description"),
                    "input_schema": function_data.get("parameters"),
                }

        return function_definition_json

    def get_tools_json(self, model: ChatModel = None, tools: list[Tool] | None = None) -> list[dict]:
        """Iterate through the tools and gather their JSON configurations."""
        # logger.debug(f"{_tag} get_tools_json [{model}]")
        tools_configs = []
        if tools is None or len(tools) == 0:
            return tools_configs

        for tool in tools:
            config = self.get_tool_config(tool.value, model)
            if config:
                tools_configs.append(config)
        return tools_configs
