#!/bin/bash

SOURCE_DIR="/mnt/maindata/data/"
TARGET_DIR="/ceph/sjones/users/lars/data/"

# Usage: ./upload_to_server.sh [--source-dir=/path] [--target-dir=/path]
for arg in "$@"; do
    case $arg in
        --source-dir=*) SOURCE_DIR="${arg#*=}" ;;
        --target-dir=*) TARGET_DIR="${arg#*=}" ;;
    esac
done

EXCLUDES=(
    --exclude="*___test__*"
    --exclude="*.csv.bak*"
    --exclude="__pycache__"
    --exclude="*.pyc*"
)

echo "Cleaning pyc/__pycache__ in $SOURCE_DIR..."
find "$SOURCE_DIR" -type f -name "*.pyc" -delete
find "$SOURCE_DIR" -type d -name "__pycache__" -exec rm -rf {} +

echo "Uploading $SOURCE_DIR → $TARGET_DIR"

echo "  Pass 1: files < 50M..."
rsync -amh --no-inc-recursive --max-size=50M --info=progress2 \
    "${EXCLUDES[@]}" "$SOURCE_DIR" "$TARGET_DIR"

echo "  Pass 2: files >= 50M..."
rsync -amh --no-inc-recursive --min-size=50M --info=progress2 \
    "${EXCLUDES[@]}" "$SOURCE_DIR" "$TARGET_DIR"

echo "Done."
