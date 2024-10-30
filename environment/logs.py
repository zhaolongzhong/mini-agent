import logging
from typing import Optional
from pathlib import Path


def get_logger(name: str, level: int = logging.INFO, filename: Optional[Path] = None) -> logging.Logger:
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(filename)s:%(lineno)d] %(message)s",
        filename=filename,
    )
    return logging.getLogger(name)


def setup_logger(id: str, log_file: Path, mode="w"):
    """
    This logger is used for logging the build process of images and containers.
    It writes logs to the log file.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"{id}.{log_file.name}")
    handler = logging.FileHandler(log_file, mode=mode)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.log_file = log_file
    return logger


def close_logger(logger):
    # To avoid too many open files
    for handler in logger.handlers:
        handler.close()
        logger.removeHandler(handler)


def setup_logging(log_dir: Path, run_id: str, task_id: str) -> logging.Logger:
    log_dir = log_dir / run_id / task_id
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "run_task.log"
    task_logger = setup_logger(task_id, log_file)
    task_logger.setLevel(logging.DEBUG)
    return task_logger
