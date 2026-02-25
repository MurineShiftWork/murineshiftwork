#!/bin/bash

INVENTORY="$(dirname "$0")/../inventory.ini"
TARGET="/mnt/maindata/data/"
REMOTE_DIR="/data"

# Usage: ./collate_data.sh [group] [--source-dir=/path] [--target-dir=/path]
for arg in "$@"; do
    case $arg in
        --source-dir=*) REMOTE_DIR="${arg#*=}" ;;
        --target-dir=*) TARGET="${arg#*=}" ;;
        --*) ;;
        *) GROUP="$arg" ;;
    esac
done

if [[ -n "$GROUP" ]]; then
    HOSTS=$(awk "/^\[$GROUP\]/{f=1;next} /^\[/{f=0} f && /ansible_host=/{print \$2}" \
            "$INVENTORY" | cut -d= -f2)
    if [[ -z "$HOSTS" ]]; then
        echo "Group '$GROUP' not found in $INVENTORY"; exit 1
    fi
else
    HOSTS=$(grep 'ansible_host=' "$INVENTORY" | awk '{print $2}' | cut -d= -f2)
fi

REMOTE_USER=$(grep 'ansible_user=' "$INVENTORY" | head -1 | cut -d= -f2)

echo "Syncing from $(echo $HOSTS | wc -w) hosts ($REMOTE_USER@host:$REMOTE_DIR) → $TARGET"

parallel --line-buffer -j 0 \
    rsync -a --no-inc-recursive --stats \
    -e "'ssh -o StrictHostKeyChecking=no -o BatchMode=yes'" \
    "$REMOTE_USER@{}:$REMOTE_DIR/" "$TARGET" \
    --exclude=".git" \
    --exclude="__pycache__" \
    --exclude=".idea" \
    --exclude="tests" \
    --exclude="*.egg-info" \
    ::: $HOSTS
