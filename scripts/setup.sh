#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

# Function to check if Rye is installed
check_rye_installed() {
    if ! command -v rye &> /dev/null; then
        echo "Rye is not installed. Installing Rye..."
        curl -sSf https://rye.astral.sh/get | bash
        echo 'source "$HOME/.rye/env"' >> ~/.bash_profile
    else
        echo "Rye is already installed."
    fi
}

check_rye_installed

rye config --set-bool behavior.use-uv=true

# Sync dependencies
rye sync --all-features
