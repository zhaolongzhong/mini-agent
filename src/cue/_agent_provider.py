import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

from .config import get_settings
from .schemas import AgentConfig, FeatureFlag
from .schemas.personality import PersonalityConfig
from .tools._tool import Tool
from .llm.llm_model import ChatModel

logger = logging.getLogger(__name__)

default_model = ChatModel.GPT_4O_MINI.id

main_agent = AgentConfig(
    id="main",
    name="main",
    is_primary=True,
    description="Is main task executor and coordinator.",
    instruction="You are primary assistant.",
    model=ChatModel.GPT_4O_MINI.id,
    temperature=0.8,
    max_tokens=5000,
    max_context_tokens=12000,
    tools=[Tool.Edit, Tool.Bash, Tool.Memory, Tool.Coordinate],
    feature_flag=FeatureFlag(enable_services=True, enable_storage=True),
    api_key=get_settings().OPENAI_API_KEY,
)

agent_o = AgentConfig(
    id="agent_o",
    name="agent_o",
    description="Is very good at readoning, analyzing problems, be able to deep dive on a topic.",
    instruction="You are an expert AI assistant with advanced reasoning capabilities.",
    model=ChatModel.O1_MINI.id,
    tools=[Tool.Edit],
    api_key=get_settings().OPENAI_API_KEY,
)

agent_claude = AgentConfig(
    id="agent_claude",
    description="Is very good at coding and also provide detail reasoning on a topic.",
    instruction="You are an expert AI assistant with advanced reasoning capabilities.",
    model=ChatModel.CLAUDE_3_5_SONNET_20241022.id,
    tools=[Tool.Edit],
    api_key=get_settings().ANTHROPIC_API_KEY,
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

    DEFAULT_CONFIG_PATHS = [
        Path(__file__).parent / "default/agents.json",  # Package default
        Path.home() / ".config/cue/agents.json",
        Path.home() / ".cue/agents.json",
        Path("/etc/cue/agents.json"),
        Path("temp/agent_dev.json"),  # For development
    ]

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = self._find_config_file(config_file)
        self._personality_templates = {}
        self._default_configs = {
            main_agent.id: main_agent,
            agent_o.id: agent_o,
            # "agent_claude": agent_claude,
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

    def _find_config_file(self, config_file: Optional[Path] = None) -> Optional[Path]:
        """Find the first available config file from specified or default locations."""
        if config_file and config_file.exists():
            return config_file
            
        for path in self.DEFAULT_CONFIG_PATHS:
            if path.exists():
                logger.info(f"Found agent config file at: {path}")
                return path
                
        logger.warning("No agent config file found in default locations")
        return None

    def _load_custom_configs(self) -> List[AgentConfig]:
        """Load custom agent configurations from file and convert to AgentConfig objects."""
        if not self.config_file:
            return []
            
        try:
            with open(self.config_file, encoding="utf-8") as f:
                config_data = json.load(f)

            # Load personality templates if present
            self._personality_templates = config_data.get("personality_templates", {})
            
            configs = []
            for agent_dict in config_data.get("agents", []):
                try:
                    # Convert dict to AgentConfig
                    agent_config = self._create_agent_config(agent_dict)
                    logger.debug(f"Load agent id: {agent_config.id}, name: {agent_config.name}")
                    if not agent_config.id:
                        agent_config.id = self._get_agent_id(agent_config)
                        
                    # Apply personality template if specified
                    if template_name := agent_dict.get("personality_template"):
                        if template := self._personality_templates.get(template_name):
                            agent_config.personality = self._create_personality_config({
                                **template,
                                **(agent_dict.get("personality", {}))  # Override with custom personality settings
                            })
                            
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
        tool_map = {t.value.lower(): t for t in Tool}
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
            client_id=config_dict.get("client_id", None),
            name=config_dict.get("name", "default"),
            description=config_dict.get("description"),
            instruction=config_dict.get("instruction"),
            model=config_dict.get("model", "gpt-4o-mini"),
            project_context_path=config_dict.get("project_context_path"),
            tools=tools,
            is_primary=config_dict.get("is_primary", False),
            temperature=config_dict.get("temperature", 0.7),
            max_tokens=config_dict.get("max_tokens", 1000),
            feature_flag=FeatureFlag(**config_dict.get("feature_flag", {})),
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

    def _create_personality_config(self, personality_dict: Dict) -> PersonalityConfig:
        """Create a PersonalityConfig from a dictionary, with validation."""
        try:
            return PersonalityConfig(**personality_dict)
        except ValueError as e:
            logger.error(f"Error creating personality config: {e}")
            return PersonalityConfig()  # Return default config on error

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
