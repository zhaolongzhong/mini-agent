# Evals Environment

This project provides an environment for running evaluation tasks in Docker containers, allowing for parallel execution and easy management of task results.

## Table of Contents

- [Getting Started](#getting-started)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [File Structure](#file-structure)
- [Workflow](#workflow)

## Getting Started

Follow these steps to set up and run the Evals Environment:

### Prerequisites

- Docker (ensure it's installed and running)
- Python 3.9+
- pip (Python package manager)

### Installation

1. Create and activate a virtual environment:

   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the example evaluation tasks:

1. Ensure Docker is running on your system.
2. Activate your Python virtual environment if not already active.
3. Run the example script:
   ```
   python run_example.py
   ```
   This will simulate running two example tasks.
4. Find the results in the `logs/run_dir` directory.

## File Structure

- `run_example.py`: The entry point script that runs all evaluation tasks in Docker containers in parallel.
- `task_run.py`: Converts your task to a `TaskRun` object, enriching it with run info (e.g., run_id, run_dir for logs and output).
- `assets/`: A folder containing essential files for task execution:
  - `entrypoint.sh`: Sets up the environment, installs dependencies, and starts `run_task.py`.
  - `run_task.py`: Executes a single evaluation task.
  - Other task-specific assets needed for evaluations.
- `container.py`: Contains container utility functions (e.g., `run_in_container()`).
- `docker_image_utils.py`: Provides utility functions for building Docker images.

## Workflow

1. `run_example.py` initiates evaluation tasks in parallel and runs them in containers.
2. Each container executes the agent to work on the assigned task.
3. Results are saved in the `/home/output` folder within the container.
4. Output is copied to the path specified in `run_example.py`.
