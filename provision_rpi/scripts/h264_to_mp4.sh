#!/bin/bash

SOURCE_DIR="/mnt/maindata/data/"
FPS=60

# Usage: ./h264_to_mp4.sh [--source-dir=/path] [--fps=N]
for arg in "$@"; do
    case $arg in
        --source-dir=*) SOURCE_DIR="${arg#*=}" ;;
        --fps=*)        FPS="${arg#*=}" ;;
    esac
done

# Check for MP4Box (gpac)
if ! command -v MP4Box &>/dev/null; then
    echo "MP4Box not found (package: gpac)."
    read -rp "Install gpac now? [y/N] " ans
    if [[ "$ans" =~ ^[Yy]$ ]]; then
        sudo apt-get install -y gpac || { echo "Install failed."; exit 1; }
    else
        echo "Aborting."; exit 1
    fi
fi

echo "Converting .h264 → .mp4 in $SOURCE_DIR at ${FPS} fps"

find "$SOURCE_DIR" -type f -name "*.h264" -print0 |
    while IFS= read -r -d '' file; do
        converted="${file}.mp4"
        if [[ -f "$converted" ]]; then
            continue
        fi
        echo "  => $file"
        MP4Box -fps "$FPS" -add "$file" "$converted"
    done

echo "Done."
