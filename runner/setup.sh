#!/bin/bash

# Get the directory where the script is located (cue/runner/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script's directory
cd "$SCRIPT_DIR"

# Create and activate virtual environment in the same directory as the script
python -m venv .venv
source .venv/bin/activate

# Install the current directory (runner) in editable mode with dev dependencies
pip install -e ".[dev]"
