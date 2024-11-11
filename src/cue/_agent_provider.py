import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

from .schemas import AgentConfig
from .tools._tool import Tool
from .llm.llm_model import ChatModel

logger = logging.getLogger(__name__)

default_model = ChatModel.GPT_4O_MINI.id

main_agent = AgentConfig(
    id="main",
    is_primary=True,
    description="Is main task executor and coordinator.",
    instruction="You are primary assistant.",
    model=ChatModel.GPT_4O_MINI.id,
    temperature=0.8,
    max_tokens=2000,
    tools=[Tool.Edit, Tool.Bash, Tool.Memory, Tool.Coordinate],
    enable_services=True,
)

agent_o = AgentConfig(
    id="agent_o",
    description="Is very good at readoning, analyzing problems, be able to deep dive on a topic.",
    instruction="You are an expert AI assistant with advanced reasoning capabilities.",
    model=ChatModel.O1_MINI.id,
    tools=[Tool.Edit],
)

agent_claude = AgentConfig(
    id="agent_claude",
    description="Is very good at coding and also provide detail reasoning on a topic.",
    instruction="You are an expert AI assistant with advanced reasoning capabilities.",
    model=ChatModel.GPT_4O.id,
    tools=[Tool.Edit],
)

system_operator = AgentConfig(
    id="system_operator",
    description="Is system operations specialist, be able to run python code or script, and execute bash command.",
    instruction="You are able to read file, write content to file, run python code or script, and execute bash command.",
    model=ChatModel.GPT_4O.id,
    tools=[Tool.Edit, Tool.Python, Tool.Bash],
)

browse_agent = AgentConfig(
    id="browse_agent",
    description="Is able to search internet and browse web page or search news.",
    instruction="Search internet, extract relevant information, verify reliability, report limitations.",
    model=default_model,
    tools=[Tool.Browse],
)

email_agent = AgentConfig(
    id="email_manager",
    description="Is able to read and sand emails and other email operations.",
    instruction="Manage email operations using available Gmail commands.",
    model=default_model,
    tools=[Tool.Email],
)

drive_agent = AgentConfig(
    id="google_drive_manager",
    description="Is able to access google drive, read file from drive or upload file to drive, or other operations.",
    instruction="Manage Google Drive operations using available commands.",
    model=default_model,
    tools=[Tool.Drive],
)


class AgentProvider:
    """Provides access to agent configurations and manages agent creation."""

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file
        self._default_configs = {
            "main": main_agent,
            # "agent_o": agent_o,
            # "agent_claude": agent_claude,
            # "system_operator": system_operator,
            # "browse_agent": browse_agent,
            # "email_manager": email_agent,
            # "google_drive_manager": drive_agent,
        }
        self.configs = None

    def get_configs(self) -> Dict[str, AgentConfig]:
        if self.configs:
            return self.configs

        configs = {}
        if self.config_file:
            custom_configs = self._load_custom_configs()
            # Update configs with custom ones, allowing overrides
            for config in custom_configs:
                agent_id = self._get_agent_id(config)
                if agent_id:
                    configs[agent_id] = config
        if not configs:
            logger.info("No agents found in config file, use default agents.")
            configs = self._default_configs.copy()
        self.configs = configs
        return configs

    def get_primary_agent(self) -> Optional[AgentConfig]:
        """Get the primary agent configuration."""
        configs = self.get_configs()
        primary_id = self.find_primary_agent_id(list(configs.values()))
        return configs.get(primary_id)

    def _load_custom_configs(self) -> List[AgentConfig]:
        """Load custom agent configurations from file and convert to AgentConfig objects."""
        try:
            with open(self.config_file, encoding="utf-8") as f:
                agents_data = json.load(f)

            configs = []
            for agent_dict in agents_data.get("agents", []):
                try:
                    # Convert dict to AgentConfig
                    agent_config = self._create_agent_config(agent_dict)
                    if not agent_config.id:
                        agent_config.id = self._get_agent_id(agent_config)
                    configs.append(agent_config)
                except ValueError as e:
                    logger.error(f"Error creating agent config: {e}")
                    continue

            count = len(configs)
            if count > 0:
                logger.info(f"Successfully loaded {count} agent configurations from '{self.config_file}'.")
            return configs

        except FileNotFoundError:
            logger.error(f"Agents configuration file '{self.config_file}' not found.")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing '{self.config_file}': {e}")
            return []

    def _create_agent_config(self, config_dict: Dict) -> AgentConfig:
        """Convert dictionary to AgentConfig with validation."""
        required_fields = {"model"}
        missing_fields = required_fields - set(config_dict.keys())

        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        tools = []
        tool_names = config_dict.get("tools", [])
        tool_map = {t.name.lower(): t for t in Tool}
        for tool_name in tool_names:
            tool_key = tool_name.lower()
            if tool_key in tool_map:
                tools.append(tool_map[tool_key])
            else:
                logger.warning(
                    f"Unknown tool '{tool_name}', skipping. " f"Available tools: {', '.join(tool_map.keys())}"
                )

        return AgentConfig(
            id=config_dict.get("id"),
            name=config_dict.get("name", "default"),
            description=config_dict.get("description"),
            instruction=config_dict.get("instruction"),
            model=config_dict.get("model", "gpt-4o-mini"),
            project_context_path=config_dict.get("project_context_path"),
            tools=tools,
            is_primary=config_dict.get("is_primary", False),
            temperature=config_dict.get("temperature", 0.7),
            max_tokens=config_dict.get("max_tokens", 1000),
            enable_services=config_dict.get("enable_external_memory", False),
        )

    @staticmethod
    def _get_agent_id(config: AgentConfig) -> Optional[str]:
        """Extract agent ID from config, falling back to normalized name."""
        agent_id = config.id
        if not agent_id:
            name = config.name
            agent_id = name.lower().replace(" ", "_") if name else None
            config.id = agent_id
        return agent_id

    @staticmethod
    def find_primary_agent_id(configs: list[AgentConfig]) -> str:
        """Find the primary agent ID or default to first config."""
        for config in configs:
            if config.is_primary:
                return config.id
        first_agent = configs[0]
        first_agent.is_primary = True
        first_agent_id = first_agent.id
        logger.warning(f"No primary agent found, using first available agent: {first_agent_id}")
        return first_agent_id
