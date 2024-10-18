import argparse
import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import docker
from tqdm import tqdm

from environment.constants import RUN_DIR
from environment.container import run_in_container
from environment.task_run import TaskRun
from environment.utils import generate_session_id, get_logger, setup_logging

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)


def get_run_assets_path() -> Path:
    return Path(__file__).parent / "assets"


async def task_wrapper(
    client: docker.DockerClient,
    executor: ThreadPoolExecutor,
    loop: asyncio.AbstractEventLoop,
    pbar: tqdm,
    task_run: TaskRun,
    results: dict[str, Any],
) -> None:
    task_logger = setup_logging(
        log_dir=RUN_DIR,
        run_id=task_run.run_id,
        task_id=task_run.task_id,
    )
    task_logger.debug("Starting task...")

    try:
        start_time = time.time()
        result = await loop.run_in_executor(
            executor,
            run_in_container,
            client,
            task_run,
            task_logger,
            True,  # retain_container
            {},  # env vars
        )
        end_time = time.time()

        results[task_run.task_id] = {
            "success": True,
            "result": result,
            "total_duration": round(end_time - start_time, 2),
        }
    except Exception as e:
        logger.error(f"Error in task {task_run.task_id}: {e}")
        results[task_run.task_id] = {"success": False, "error": str(e)}
    finally:
        pbar.update(1)


async def run_tasks(tasks: list[TaskRun], max_concurrent: int) -> dict[str, Any]:
    results: dict[str, Any] = {}

    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        loop = asyncio.get_running_loop()
        client = docker.from_env()

        pbar = tqdm(total=len(tasks), desc="Running Tasks")
        coroutines = [task_wrapper(client, executor, loop, pbar, task, results) for task in tasks]
        await asyncio.gather(*coroutines)
        pbar.close()

    return results


async def main(args: argparse.Namespace) -> None:
    MAX_CONCURRENT_TASKS = args.max_concurrent
    run_id = generate_session_id()
    run_assets_path = get_run_assets_path()
    base_image = "evals_example"

    tasks = [
        TaskRun(
            task_id=f"{i}",
            run_id=run_id,
            run_dir=RUN_DIR,
            run_asset_path=run_assets_path,
            image=base_image,
            instruction=f"Task instruction: {i}",
        )
        for i in range(args.num_tasks)
    ]
    logger.debug(f"Starting {len(tasks)} tasks")

    results = await run_tasks(tasks, MAX_CONCURRENT_TASKS)

    success_count = sum(1 for res in results.values() if res.get("success"))
    failure_count = len(results) - success_count
    logger.info(f"Tasks completed: {success_count} succeeded, {failure_count} failed.")

    for task_id, res in list(results.items())[:5]:
        logger.info(f"Task {task_id}: {res}")
    logger.debug(f"Results:\n{json.dumps(results, indent=4)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run multiple Docker container tasks concurrently.")
    parser.add_argument("--max-concurrent", type=int, default=10, help="Maximum number of concurrent tasks")
    parser.add_argument("--num-tasks", type=int, default=2, help="Number of tasks to run")
    args = parser.parse_args()
    asyncio.run(main(args))
