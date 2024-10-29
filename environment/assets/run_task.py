"""
run_task.py

This script performs a simple task of writing instructions and task-specific content to an output file.
It is designed to be executed within a Docker container, receiving parameters via command-line arguments.

Additionally, it includes asynchronous capabilities to handle future asynchronous tasks seamlessly.

Usage:
    python run_task.py --task_id <TASK_ID> --instruction <INSTRUCTION> --output-folder <OUTPUT_FOLDER>

Arguments:
    --task_id         The unique identifier for the task.
    --instruction     The instruction or command to execute.
    --output-folder   The directory where output files will be written.
"""

import asyncio
import logging
import argparse
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Run agent")
    parser.add_argument("--task_id", type=str, required=True, help="Task ID")
    parser.add_argument("--instruction", type=str, required=True, help="Instruction")
    parser.add_argument("--output-folder", type=str, required=True, help="Output folder to write the file")
    args = parser.parse_args()

    if not args.task_id.strip():
        parser.error("The --task_id argument cannot be empty.")

    if not args.instruction.strip():
        parser.error("The --instruction argument cannot be empty.")

    output_path = Path(args.output_folder)
    if output_path.exists() and not output_path.is_dir():
        parser.error(f"The --output-folder path '{args.output_folder}' exists and is not a directory.")

    return args


def run_task(args: argparse.Namespace) -> None:
    """
    Executes the task by writing instructions and task-specific content to a file.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Raises:
        PermissionError: If there are permission issues accessing the output directory.
        IOError: If an I/O error occurs during file operations.
        Exception: For any unexpected errors.
    """
    task_id: str = args.task_id
    instruction: str = args.instruction
    output_folder: Path = Path(args.output_folder)

    try:
        output_folder.mkdir(parents=True, exist_ok=True)
        file_path: Path = output_folder / "run_task_output.txt"
        logger.debug(f"Running task {task_id} with instruction: {instruction}")

        with file_path.open("w") as f:
            f.write(f"Instruction: {instruction}\n")
            f.write(f"Hello, this is a simple file content for task {task_id}.\n")

        logger.debug(f"Content written to {file_path}.")
    except PermissionError as pe:
        logger.error(f"Permission denied while accessing {output_folder}: {pe}")
        raise
    except OSError as ioe:
        logger.error(f"I/O error occurred: {ioe}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise


async def additional_async_task(task_id: str) -> None:
    """
    A simple asynchronous task that simulates an asynchronous operation.

    Args:
        task_id (str): The unique identifier for the task.
    """
    try:
        logger.debug(f"Starting additional asynchronous task for Task ID: {task_id}")
        # Simulate an asynchronous operation (e.g., network request, I/O-bound task)
        await asyncio.sleep(2)  # Simulates a delay
        logger.debug(f"Completed additional asynchronous task for Task ID: {task_id}")
    except Exception as e:
        logger.error(f"An error occurred in additional_async_task: {e}")
        raise


async def main() -> None:
    """
    Main function to parse arguments and execute tasks concurrently.
    """
    args: argparse.Namespace = parse_args()
    logger.debug(f"Main started with args: {args}")

    run_task_coroutine = asyncio.to_thread(run_task, args)
    async_task_coroutine = additional_async_task(args.task_id)
    await asyncio.gather(run_task_coroutine, async_task_coroutine)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except PermissionError:
        logger.error("Failed due to permission issues.")
        exit(2)
    except OSError:
        logger.error("Failed due to an I/O error.")
        exit(3)
    except Exception as e:
        logger.error(f"An unexpected error occurred in run_task: {e}")
        exit(1)
