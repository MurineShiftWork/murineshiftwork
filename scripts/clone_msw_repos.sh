#!/usr/bin/env bash
# Clone (or pull) all MSW workspace repos into a project directory.
# Usage: clone_msw_repos.sh <project_dir>

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <project_dir>"
    exit 1
fi

PROJECT_DIR="$1"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

REPOS=(
    "https://github.com/larsrollik/murineshiftwork"
    "https://github.com/MurineShiftWork/msw-core"
    "https://github.com/MurineShiftWork/msw-io"
    "https://github.com/MurineShiftWork/msw-tasks-core"
    "https://github.com/MurineShiftWork/msw-tasks-lab"
    "https://github.com/MurineShiftWork/msw-tasks-example"
    "https://github.com/MurineShiftWork/msw-agent"
    "https://github.com/MurineShiftWork/msw-plugin-api"
    "https://github.com/MurineShiftWork/msw-open-ephys"
    "https://github.com/MurineShiftWork/msw-flir-bonsai"
    "https://github.com/MurineShiftWork/msw-labwatch"
    "https://github.com/MurineShiftWork/acquisition-namespace"
    "https://github.com/MurineShiftWork/one-axis-stage"
    "https://github.com/MurineShiftWork/pypulsepal"
    "https://github.com/MurineShiftWork/rpi-camera-ensemble"
    "https://github.com/MurineShiftWork/rpi-camera-colony"
    "https://github.com/MurineShiftWork/serial-scale-bench"
    "https://github.com/MurineShiftWork/serial-scale-hx711"
    "https://github.com/MurineShiftWork/ttl-barcoder"
)

for url in "${REPOS[@]}"; do
    name=$(basename "$url")
    if [[ -d "$name/.git" ]]; then
        echo "Pulling $name..."
        git -C "$name" pull --ff-only
    else
        echo "Cloning $name..."
        git clone "$url"
    fi
done

echo "Done. All repos in $PROJECT_DIR"
