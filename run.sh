#!/usr/bin/env bash

set -euo pipefail

use_database=false

while getopts "d" opt; do
  case ${opt} in
    d )
      use_database=true
      ;;
    \? )
      ;;
  esac
done

if [ "$use_database" = true ]; then
    python3 main_with_db.py
else
    python3 main.py
fi
