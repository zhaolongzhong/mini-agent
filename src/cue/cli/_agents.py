from typing import Dict

from ..llm.llm_model import ChatModel
from ..schemas import AgentConfig
from ..tools._tool import Tool

default_model = ChatModel.GPT_4O_MINI

main_agent = AgentConfig(
    id="main",
    name="main",
    description="Is main task executor and coordinator with other agents.",
    instruction="Analyze requests, delegate to specialists, maintain context, and synthesize outputs. Avoid using specialist tools directly.",
    model=ChatModel.GPT_4O,
    temperature=0.8,
    max_tokens=2000,
    tools=[Tool.Read],
)

system_operator = AgentConfig(
    id="system_operator",
    name="system_operator",
    description="Is system operations specialist, be able to read file, write content to file, run python code or script, and execute bash command..",
    instruction="You are able to read file, write content to file, run python code or script, and execute bash command.",
    model=default_model,
    tools=[Tool.Read, Tool.Write, Tool.Python, Tool.Bash],
)

browse_agent = AgentConfig(
    id="browse_agent",
    name="browse_agent",
    description="Is able to search internet and browse web page or search news.",
    instruction="Search internet, extract relevant information, verify reliability, report limitations.",
    model=default_model,
    tools=[Tool.Browse],
)

email_agent = AgentConfig(
    id="email_manager",
    name="email_manager",
    description="Is able to read and sand emails and other email operations.",
    instruction="Manage email operations using available Gmail commands.",
    model=default_model,
    tools=[Tool.Email],
)

drive_agent = AgentConfig(
    id="google_drive_manager",
    name="google_drive_manager",
    description="Is able to access google drive, read file from drive or upload file to drive, or other operations.",
    instruction="Manage Google Drive operations using available commands.",
    model=default_model,
    tools=[Tool.Drive],
)


def get_agent_configs() -> tuple[Dict[str, AgentConfig], str]:
    """Get predefined agent configurations and main agent ID.

    Returns:
        Agent configurations dictionary and main agent ID
    """
    configs = {
        "main": main_agent,
        "system_operator": system_operator,
        "browse_agent": browse_agent,
        "email_manager": email_agent,
        "google_drive_manager": drive_agent,
    }
    return (configs, "main")
