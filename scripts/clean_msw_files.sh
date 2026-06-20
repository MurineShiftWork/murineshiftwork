#!/usr/bin/env bash
# clean_msw_files.sh — Remove known noise events from .msw.csv behaviour files.
#
# Currently removes rows containing 'Port4' (hardware noise event present on
# some Bpod configurations) from every .msw.csv file found under DATA_DIR.
# Originals are backed up with a timestamp suffix before modification.
#
# Usage:
#   ./clean_msw_files.sh --data-dir=<path> [--event=<string>] [--dry-run]
#
# Options:
#   --data-dir=PATH   Root directory to search for .msw.csv files (required)
#   --event=STRING    Event name to remove (default: Port4)
#   --dry-run         Show which files would be modified; do not change anything
#
# Example:
#   ./clean_msw_files.sh --data-dir=/data/data
#   ./clean_msw_files.sh --data-dir=/data/data --event=Port4 --dry-run

set -euo pipefail

DATA_DIR=''
EVENT='Port4'
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --data-dir=*)  DATA_DIR="${arg#*=}" ;;
        --event=*)     EVENT="${arg#*=}" ;;
        --dry-run)     DRY_RUN=true ;;
        -h|--help)
            sed -n '/^# Usage:/,/^$/p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$DATA_DIR" ]]; then
    echo "Error: --data-dir is required." >&2
    echo "Run with --help for usage." >&2
    exit 1
fi

if [[ ! -d "$DATA_DIR" ]]; then
    echo "Error: data-dir not found: $DATA_DIR" >&2
    exit 1
fi

ts=$(date +%Y%m%d_%H%M%S)
count_all=0
count_mod=0

while IFS= read -r -d '' file; do
    count_all=$((count_all + 1))
    if grep -q "$EVENT" "$file"; then
        if $DRY_RUN; then
            echo "[dry-run] would clean: $file"
        else
            cp "$file" "${file}.bak.${ts}"
            sed -i "/${EVENT}/d" "$file"
            echo "Cleaned: $file"
            count_mod=$((count_mod + 1))
        fi
    fi
done < <(find "$DATA_DIR" -name "*.msw.csv" -print0)

if $DRY_RUN; then
    echo "Dry run complete. Scanned $count_all file(s)."
else
    echo "Done. Scanned $count_all file(s), modified $count_mod."
fi
