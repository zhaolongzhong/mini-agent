import json
from pathlib import Path

from tools.read_file import read_file
from tools.run_python_script import run_python_script
from tools.write_to_file import write_to_file
from tools.scan_folder import scan_folder


class ToolManager:
    def __init__(self):
        self.tools = {
            "read_file": read_file,
            "write_to_file": write_to_file,
            "scan_folder": scan_folder,
            "run_python_script": run_python_script,
        }

    def get_tool_config(self, tool_name: str) -> dict:
        """Load the JSON configuration for a specific tool from its respective file."""
        config_path = Path(f"tools/{tool_name}.json")
        if not config_path.exists():
            return {"error": f"Configuration file for {tool_name} does not exist"}

        with config_path.open("r", encoding="utf-8") as file:
            # TODO: validate the JSON schema
            return json.load(file)

    def get_tools_json(self) -> list[dict]:
        """Iterate through the tools and gather their JSON configurations."""
        tools_configs = []
        for tool_name in self.tools:
            config = self.get_tool_config(tool_name)
            tools_configs.append(config)
        return tools_configs

    def get_tool(self, tool_name: str):
        return self.tools.get(tool_name)
