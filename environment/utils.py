import logging
import os
import shutil
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


def generate_id(length: int = 21) -> str:
    return uuid.uuid4().hex[:length]


def generate_session_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Format: YYYYMMDDHHMMSS
    unique_part = generate_id(6)
    return f"{timestamp}-{unique_part}"


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


def copy_file_or_directory(src, dest):
    """
    Helper function to copy either a file or directory to the destination.
    """
    try:
        if Path(src).is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
            print(f"Copied directory '{src}' to '{dest}'.")
        else:
            shutil.copy(src, dest)
            print(f"Copied file '{src}' to '{dest}'.")
    except Exception as e:
        print(f"Failed to copy '{src}' to '{dest}': {e}")
        traceback.print_exc()


def copy_folder(src_folder, dest_folder):
    """
    Helper function to copy all contents from a foler
    """
    # Ensure source and destination exist
    if not os.path.exists(src_folder):
        print(f"Source folder '{src_folder}' does not exist.")
        return

    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    # Copy contents of the source folder to the destination folder
    try:
        shutil.copytree(src_folder, dest_folder, dirs_exist_ok=True)
        print(f"Successfully copied '{src_folder}' to '{dest_folder}'")
    except Exception as e:
        print(f"Error during copying: {e}")
