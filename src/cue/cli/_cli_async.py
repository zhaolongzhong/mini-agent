import sys
import json
import asyncio
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor

from rich.text import Text

from ..utils import DebugUtils, console_utils, generate_run_id
from ..config import get_settings
from ..schemas import RunMetadata
from ..utils.logs import setup_logging
from ._cli_command import CliCommand, parse_command
from .._agent_manager import AgentManager
from .._agent_provider import AgentProvider

setup_logging()

logger = logging.getLogger(__name__)


class CLI:
    def __init__(self, args):
        self.logger = logger
        self.console_utils = console_utils

        self.agent_manager = AgentManager()
        self.executor = ThreadPoolExecutor()
        self.agent_provider = AgentProvider(get_settings().AGENTS_CONFIG_FILE)
        self.primary_agent_config = self.agent_provider.get_primary_agent()
        self.active_agent_id = None
        self.enable_external_memory = False

        self.enable_debug_turn = args.enable_debug_turn
        self._config_agents()

    def _config_agents(self):
        # Register all agents
        self.agents = {
            config.id: self.agent_manager.register_agent(config)
            for config in self.agent_provider.get_configs().values()
        }

    async def _get_user_input_async(self, prompt: str):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: self.console_utils.console.input(prompt))

    async def run(self):
        self.enable_external_memory = self.primary_agent_config.enable_external_memory
        await self.agent_manager.initialize(enable_external_memory=self.enable_external_memory)
        self.agent_manager.primary_agent = self.agents[self.primary_agent_config.id]
        self.agent_manager.active_agent = self.agent_manager.primary_agent
        self.logger.debug("Running the CLI. Commands: 'exit'/'quit' to exit, 'snapshot'/'-s' to save context")

        try:
            run_metadata = RunMetadata(
                run_id=generate_run_id(),
                enable_turn_debug=self.enable_debug_turn,
                enable_external_memory=self.primary_agent_config.enable_external_memory,
            )

            while True:
                active_agent_id = self.agent_manager.active_agent.id
                user_input = await self._get_user_input_async("")

                # Parse command
                command, message = parse_command(user_input)

                # Handle empty or too short messages
                if not command and (not message or len(message) < 3):
                    self.console_utils.print_error_msg(active_agent_id, "Message must be at least 3 characters long.")
                    continue

                # Handle commands
                if command == CliCommand.HELP:
                    from ._cli_command import print_help

                    print_help(self.console_utils.console, message)
                    continue
                if command == CliCommand.EXIT:
                    self.logger.info("Exit command received. Shutting down.")
                    break

                if command == CliCommand.SNAPSHOT:
                    try:
                        snapshot_path = self.agent_manager.active_agent.snapshot()
                        success_msg = Text("[System]: ", style="system")
                        success_msg.append(f"Snapshot saved to {snapshot_path}", style="success")
                        self.console_utils.console.print(success_msg)

                        # If there was additional message content, process it
                        if message and len(message) >= 3:
                            user_input = message
                        else:
                            continue
                    except Exception as e:
                        error_msg = Text("[System]: ", style="system")
                        error_msg.append(f"Failed to save snapshot: {str(e)}", style="error")
                        self.console_utils.console.print(error_msg)
                        continue

                self.logger.debug(f"{user_input}")
                run_metadata.user_messages.append(f"{user_input}")
                DebugUtils.log_chat({"user": user_input})

                if self.enable_external_memory:
                    await self.agent_manager.send_user_message(user_input)
                else:
                    await self.agent_manager.run(active_agent_id, user_input, run_metadata)

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
    parser.add_argument("-d", "--enable_debug_turn", action="store_true", help="Pause for each run loop turn.")
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

    cli = CLI(args=args)

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
