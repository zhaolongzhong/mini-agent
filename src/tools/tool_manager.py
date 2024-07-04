import json
from pathlib import Path

from llm_client.llm_model import ChatModel
from tools.execute_shell_command import execute_shell_command
from tools.read_file import read_file
from tools.run_python_script import run_python_script
from tools.scan_folder import scan_folder
from tools.write_to_file import write_to_file
from utils.logs import logger

_tag = "[ToolManager]"


class ToolManager:
    def __init__(self):
        self.tools = {
            "read_file": read_file,
            "write_to_file": write_to_file,
            "scan_folder": scan_folder,
            "run_python_script": run_python_script,
            "execute_shell_command": execute_shell_command,
        }

        self.tools_path = Path(__file__).parent
        logger.debug(f"{_tag} tools_path: {self.tools_path}")

    def get_tool_config(
        self,
        tool_name: str,
        model: str = ChatModel.GPT_4O.value,
    ) -> dict | None:
        """Load the JSON configuration for a specific tool from its respective file."""
        config_path = Path(f"{self.tools_path}/{tool_name}.json")
        logger.debug(f"{_tag} get_tool_config [{model}][{tool_name}]")
        if not config_path.exists():
            logger.error(f"Configuration file for {tool_name} does not exist")
            return None

        with config_path.open("r", encoding="utf-8") as file:
            definition_data = json.load(file)
            if model is None or "gpt-4" in model or "gemini" in model:
                return definition_data
            elif "claude" in model:
                # https://docs.anthropic.com/en/docs/build-with-claude/tool-use
                if "function" in definition_data:
                    function_data = definition_data["function"]
                    updated_definition_data = {
                        "name": function_data.get("name"),
                        "description": function_data.get("description"),
                        "input_schema": function_data.get("parameters"),
                    }
                    return updated_definition_data
            else:
                logger.error(f"Unsupported model: {model}")
                raise ValueError(f"Unsupported model: {model}")

    def get_tools_json(self, model: str = None) -> list[dict]:
        """Iterate through the tools and gather their JSON configurations."""
        logger.debug(f"{_tag} get_tools_json [{model}]")
        tools_configs = []
        for tool_name in self.tools:
            config = self.get_tool_config(tool_name, model)
            if config:
                tools_configs.append(config)
        return tools_configs

    def get_tool(self, tool_name: str):
        return self.tools.get(tool_name)
