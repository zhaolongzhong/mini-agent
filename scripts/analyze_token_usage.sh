#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

echo "Running usage analysis ..."
rye run python -m src.cue.utils.usage_utils
