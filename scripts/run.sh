#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

export ENVIRONMENT="development"
rye run cue -r
