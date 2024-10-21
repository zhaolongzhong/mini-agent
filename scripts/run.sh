#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

export ENVIRONMENT="development"
export CUE_LOG="debug"

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run the rye command, it runs src.cue.cli._cli_async
# rye run cue -r
rye run python -W ignore::RuntimeWarning -m src.cue.cli._cli_async -r
