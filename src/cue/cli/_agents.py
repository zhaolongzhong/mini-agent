from typing import Dict

from ..llm.llm_model import ChatModel
from ..schemas import AgentConfig
from ..tools._tool import Tool


def get_agent_configs() -> tuple[Dict[str, AgentConfig], str]:
    """
    Returns a dictionary of predefined agent configurations and the default main(orchestrator) agent ID.
    Each configuration defines an agent's specialized capabilities, collaboration patterns, and operating parameters.

    Returns:
        tuple[Dict[str, AgentConfig], str]: Dictionary mapping agent IDs to their configurations and the main agent ID
    """
    configs = {
        "main": AgentConfig(
            id="main",
            name="main",
            description="Lead coordinator that analyzes tasks, delegates to specialized agents (File Operator and browser), manages information flow, and synthesizes results. Acts as the central hub for team collaboration.",
            instruction="""Coordinate the AI team by analyzing requests, delegating tasks to specialists (File Operator and browser), maintaining context, and synthesizing outputs. Provide clear instructions to agents, facilitate collaboration, and avoid using specialist tools directly.""",
            model=ChatModel.GPT_4O_MINI,
            temperature=0.8,
            max_tokens=2000,
            tools=[Tool.FileRead],
        ),
        "file_operator": AgentConfig(
            id="file_operator",
            name="file_operator",
            description="System operations specialist managing file operations, command execution, and local resources. Collaborates with main and browser for task coordination.",
            instruction="""Execute system operations as directed by main. Collaborate with browser when tasks require both system operations and internet data. Provide operation feedback, alert on risks, maintain security, and handle errors gracefully.""",
            model=ChatModel.GPT_4O_MINI,
            tools=[Tool.FileRead, Tool.FileWrite, Tool.ShellTool],
        ),
        "browser": AgentConfig(
            id="browser",
            name="browser",
            description="Internet research specialist handling web searches, content analysis, and information synthesis. Collaborates with main and File Operator to support tasks with data gathering and verification.",
            instruction="""Conduct web research as directed by main. Collaborate with File Operator when tasks involve both internet data and local system operations. Extract and summarize relevant information, verify reliability, and report access limitations.""",
            model=ChatModel.GPT_4O_MINI,
            tools=[Tool.BrowseWeb],
        ),
    }

    return (configs, "main")
