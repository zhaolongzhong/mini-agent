#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

# Load the .env.test file
if [ -f .env.test ]; then
  export $(cat .env.test | xargs)
fi

RUN_EVALUATION=false

# Parse command-line options
while getopts ":e" opt; do
  case ${opt} in
    e )
      RUN_EVALUATION=true
      ;;
    \? )
      echo "Usage: cmd [-e]"
      exit 1
      ;;
  esac
done

echo "Running tests ..."

echo "Running unit tests ..."
rye run pytest -s -m unit

if [ "$RUN_EVALUATION" = true ]; then
  echo "Running evaluation tests ..."
  rye run pytest -s -m evaluation
fi
