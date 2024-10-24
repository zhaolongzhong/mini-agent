import argparse
import asyncio
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.text import Text
from rich.theme import Theme

from .._agent_manager import AgentManager
from ..cli._agents import get_agent_configs
from ..schemas import CompletionResponse, RunMetadata
from ..utils.logs import setup_logging

setup_logging()

custom_theme = Theme(
    {
        "user": "bold blue",
        "cue": "bold green",
        "error": "bold red",
    }
)

logger = logging.getLogger(__name__)


class CLI:
    def __init__(self):
        self.logger = logger
        self.console = Console(theme=custom_theme)

        self.agent_manager = AgentManager()
        self.executor = ThreadPoolExecutor()
        configs, active_agent_id = get_agent_configs()
        self.configs = configs
        self.active_agent_id = active_agent_id
        self._config_agents()

    def _config_agents(self) -> str:
        # Register all agents
        self.agents = {config.id: self.agent_manager.register_agent(config) for _, config in self.configs.items()}

        # Add transfer tool to all agents
        for agent_id in self.agents:
            self.agent_manager.add_tool_to_agent(agent_id, self.agent_manager.chat_with_agent)
        return self.active_agent_id

    async def _get_user_input_async(self, prompt: str):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: self.console.input(prompt))

    async def run(self):
        self.logger.info("Running the CLI. Type 'exit' or 'quit' to exit.")
        try:
            self.agent_manager.set_active_agent(self.active_agent_id)
            run_metdata = RunMetadata()
            while True:
                active_agent_id = self.agent_manager.active_agent.id
                user_prompt = Text("[User]: ", style="user")
                user_input = await self._get_user_input_async(user_prompt)
                if len(user_input) < 3:
                    error_message = Text("[Cue ]: ", style="cue")
                    error_message.append("Message must be at least 3 characters long.", style="error")
                    self.console.print(error_message)
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    self.logger.info("Exit command received. Shutting down.")
                    break
                self.logger.debug(f"{user_input}")

                run_metdata.user_messages.append(f"user_says_to_agent_b: {user_input}")
                response = await self.agent_manager.run(active_agent_id, user_input, run_metdata)
                if response:
                    agent_id = self.agent_manager.active_agent.id
                    if isinstance(response, CompletionResponse):
                        response = response.get_text()
                    else:
                        logger.error(f"Unexpected response: {response}")
                    message = Text()
                    message.append(f"[{agent_id}]: ", style="cue")
                    message.append(str(response), style="cue")
                    self.console.print(message)
        except Exception as e:
            self.logger.exception(f"An error occurred: {e}")
            raise
        finally:
            self.logger.info("Cleaning up the agent manager...")
            await self.agent_manager.clean_up()
            self.executor.shutdown(wait=True)
            self.logger.debug("Cleanup complete.")


def _parse_args():
    parser = argparse.ArgumentParser(description="Cue CLI: An interactive asynchronous client.")
    parser.add_argument("-v", "--version", action="store_true", help="Print the version of the Cue client.")
    parser.add_argument("-r", "--run", action="store_true", help="Run the interactive CLI.")
    parser.add_argument("-c", "--config", action="store_true", help="Print the default configuration.")
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (overrides environment variable).",
    )
    parser.add_argument("--log-file", type=str, help="Path to a file to log messages (overrides environment settings).")
    return parser.parse_args()


async def main(cli_instance: CLI):
    try:
        await cli_instance.run()
    except KeyboardInterrupt:
        cli_instance.logger.info("Detected keyboard interrupt. Cleaning up...")
    finally:
        await cli_instance.agent_manager.clean_up()
        cli_instance.logger.info("Cleanup complete.")


def async_main():
    args = _parse_args()

    if len(sys.argv) == 1:
        print("No arguments provided. Use -h for help.")
        sys.exit(1)

    if args.version:
        from .. import __version__

        print(f"version {__version__}")
        return

    if args.config:
        cli_temp = CLI()
        for _id, config in cli_temp.configs.items():
            print(json.dumps(config.model_dump(), indent=4, default=str))
        print(f"active agent: {cli_temp.active_agent_id}")
        return

    if args.log_level:
        logger.setLevel(getattr(logging, args.log_level.upper(), logging.DEBUG))
        logging.getLogger("httpx").setLevel(getattr(logging, logging.WARN, logging.WARN))

    if args.log_file:
        file_handler = logging.FileHandler(args.log_file, encoding="utf-8")
        formatter = logging.Formatter(
            "[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG if logger.level <= logging.DEBUG else logger.level)
        logger.addHandler(file_handler)

    cli = CLI()

    try:
        asyncio.run(main(cli))
    except KeyboardInterrupt:
        sys.stderr.write("\nKeyboard interrupt detected. Exiting...\n")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    async_main()
