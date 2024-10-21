#!/usr/bin/env bash

set -euo pipefail

# Change to the project root directory
cd "$(dirname "$0")/.."

# Function to load environment variables from a file
load_env() {
  local env_file="$1"
  if [ -f "$env_file" ]; then
    # Export variables without echoing them
    set -a
    # Use grep to ignore comments and empty lines
    # shellcheck disable=SC1091
    grep -v '^\s*#' "$env_file" | grep -v '^\s*$' > /tmp/temp_env_file
    source /tmp/temp_env_file
    rm /tmp/temp_env_file
    set +a
  fi
}

# Load the .env.test file if it exists
load_env ".env.test"

# Initialize flags for each test type
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_EVALUATION=false
RUN_SINGLE_TEST=false
TEST_PATH=""

# Function to display usage instructions
usage() {
  echo "Usage: $0 [options]"
  echo ""
  echo "Options:"
  echo "  -u    Run unit tests only"
  echo "  -i    Run integration tests only"
  echo "  -a    Run both unit and integration tests"
  echo "  -e    Run evaluation tests (requires OPENAI_API_KEY)"
  echo "  -t <test_path> Run a single test specified by the test path"
  echo "  -h    Show this help message and exit"
  echo ""
  echo "Examples:"
  echo "  $0 -u          # Run unit tests only"
  echo "  $0 -i          # Run integration tests only"
  echo "  $0 -a          # Run both unit and integration tests"
  echo "  $0 -e          # Run evaluation tests"
  echo "  $0 -t tests/evaluation/test_async_client.py::TestClientManager::test_async_client  # Run a single test"
  echo "  $0 -u -e       # Run unit and evaluation tests"
  exit 1
}

# Parse command-line options
while getopts ":uiaet:h" opt; do
  case ${opt} in
    u )
      RUN_UNIT=true
      ;;
    i )
      RUN_INTEGRATION=true
      ;;
    a )
      RUN_UNIT=true
      RUN_INTEGRATION=true
      ;;
    e )
      RUN_EVALUATION=true
      ;;
    t )
      RUN_SINGLE_TEST=true
      TEST_PATH="$OPTARG"
      ;;
    h )
      usage
      ;;
    \? )
      echo "Invalid Option: -$OPTARG" >&2
      usage
      ;;
    : )
      echo "Invalid Option: -$OPTARG requires an argument" >&2
      usage
      ;;
  esac
done

# Shift off the options and optional --
shift $((OPTIND -1))

# If no options are provided, default to running both unit and integration tests
if ! $RUN_UNIT && ! $RUN_INTEGRATION && ! $RUN_EVALUATION; then
  RUN_UNIT=true
  RUN_INTEGRATION=true
fi

# Run unit tests if flagged
if $RUN_UNIT; then
  echo "Running unit tests ..."
  rye run pytest -s -m unit
fi

# Run integration tests if flagged
if $RUN_INTEGRATION; then
  echo "Running integration tests ..."
  rye run pytest -s -m integration
fi

# Run evaluation tests if flagged
if $RUN_EVALUATION; then
  echo "Running evaluation tests ..."

  # Load the main .env file to get the API keys
  load_env ".env"

  # Check if OPENAI_API_KEY is set
  if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "Error: OPENAI_API_KEY is not set. Please set it in the .env file or as an environment variable." >&2
    exit 1
  fi

  rye run pytest -s tests/evaluation
fi

# Run a single test if flagged
if $RUN_SINGLE_TEST; then
  echo "Running single test: $TEST_PATH ..."
  
  # Check if TEST_PATH contains "evaluation" and load the .env file if necessary
  if [[ "$TEST_PATH" == *"evaluation"* ]]; then
    echo "Loading environment variables for evaluation tests..."
    load_env ".env"
  fi
  
  rye run pytest -s "$TEST_PATH"
fi

echo "All requested tests have been executed successfully."
