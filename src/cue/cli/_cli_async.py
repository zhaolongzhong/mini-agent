# src/cue/_cli_async.py
import argparse
import asyncio
import logging
import sys
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.text import Text
from rich.theme import Theme

from .._agent_manager import AgentManager
from ..llm.llm_model import ChatModel
from ..schemas import AgentConfig, CompletionResponse, FeatureFlag
from ..tools._tool import Tool
from ..utils.logs import _logger, setup_logging

setup_logging()

custom_theme = Theme(
    {
        "user": "bold blue",
        "cue": "bold green",
        "error": "bold red",
    }
)


class CLI:
    def __init__(self):
        self.logger = _logger
        self.console = Console(theme=custom_theme)
        self.agent_config = AgentConfig(
            name="cue_cli",
            model=ChatModel.GPT_4O_MINI,
            temperature=0.8,
            max_tokens=2000,
            conversation_id="",
            feature_flag=FeatureFlag(is_cli=True, is_eval=False),
            tools=[
                Tool.FileRead,
                Tool.FileWrite,
                Tool.ShellTool,
            ],
        )
        self.agent_manager = AgentManager(config=self.agent_config)
        self.executor = ThreadPoolExecutor()
        self.agent = None

    async def run(self):
        self.logger.info("Running the CLI. Type 'exit' or 'quit' to exit.")
        try:
            self.agent = await self.agent_manager.set_up(self.agent_config)
            while True:
                user_prompt = Text("[User]: ", style="user")
                user_input = await self.get_user_input_async(user_prompt)
                if len(user_input) < 3:
                    error_message = Text("[Cue ]: ", style="cue")
                    error_message.append("Message must be at least 3 characters long.", style="error")
                    self.console.print(error_message)
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    self.logger.info("Exit command received. Shutting down.")
                    break
                self.logger.debug(f"{user_input}")
                response = await self.agent.send_message(user_input)
                if response:
                    if isinstance(response, CompletionResponse):
                        response = response.get_text()
                    self.console.print(f"[Cue ]: {response}", style="cue")
        except Exception as e:
            self.logger.exception(f"An error occurred: {e}")
            raise
        finally:
            self.logger.info("Cleaning up the agent manager...")
            await self.agent_manager.clean_up()
            self.executor.shutdown(wait=True)
            self.logger.debug("Cleanup complete.")

    async def get_user_input_async(self, prompt: str):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: self.console.input(prompt))


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
        config = cli_temp.agent_config
        for key, value in config.model_dump().items():
            print(f"{key}: {value}")
        return

    if args.log_level:
        _logger.setLevel(getattr(logging, args.log_level.upper(), logging.INFO))
        logging.getLogger("httpx").setLevel(getattr(logging, logging.WARN, logging.WARN))

    if args.log_file:
        file_handler = logging.FileHandler(args.log_file, encoding="utf-8")
        formatter = logging.Formatter(
            "[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG if _logger.level <= logging.DEBUG else _logger.level)
        _logger.addHandler(file_handler)

    cli = CLI()

    try:
        asyncio.run(main(cli))
    except KeyboardInterrupt:
        sys.stderr.write("\nKeyboard interrupt detected. Exiting...\n")
        sys.exit(1)
    except Exception as e:
        _logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    async_main()
