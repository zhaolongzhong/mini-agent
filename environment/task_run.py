from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TaskRun:
    task_id: str
    run_id: str
    run_dir: Path
    run_asset_path: Path
    image: str
    instruction: str
