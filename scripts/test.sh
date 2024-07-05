#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

# Load the .env.test file
if [ -f .env.test ]; then
  export $(cat .env.test | xargs)
fi

echo "Running tests ..."
rye run test
