#!/bin/bash
set -euxo pipefail

LOGS_DIR=/home/logs
mkdir -p "$LOGS_DIR"

# Redirect all output to the log file as early as possible
exec > >(tee -a "$LOGS_DIR/entrypoint.log") 2>&1

echo "Entrypoint script is running."

# Define output directory
OUTPUT_DIR=${OUTPUT_DIR:-/home/output}
mkdir -p "$OUTPUT_DIR"

# Build the cue client
rye build 

# Install cue client, remove -q to see full installation log
pip install -q ./cue-0.1.0-py3-none-any.whl

which cue

cue -v

echo "Starting run_task.py..."

python3 run_task.py --output-folder "$OUTPUT_DIR" --task_id "$TASK_ID" --instruction "$INSTRUCTION"

cp -r "$LOGS_DIR/" "$OUTPUT_DIR/"

pwd
ls -la "$OUTPUT_DIR"
