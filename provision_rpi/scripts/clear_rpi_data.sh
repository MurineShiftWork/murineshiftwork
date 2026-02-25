#!/bin/bash

INVENTORY="$(dirname "$0")/../inventory.ini"
REMOTE_DIR="/data"

# Usage: ./clear_rpi_data.sh [group] [--source-dir=/path]
for arg in "$@"; do
    case $arg in
        --source-dir=*) REMOTE_DIR="${arg#*=}" ;;
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
HOST_COUNT=$(echo $HOSTS | wc -w)

echo "WARNING: This will delete $REMOTE_DIR/* on $HOST_COUNT hosts as $REMOTE_USER."
read -rp "Type 'yes' to confirm: " ans
[[ "$ans" != "yes" ]] && { echo "Aborted."; exit 1; }

parallel -j 0 \
    ssh -o StrictHostKeyChecking=no -o BatchMode=yes \
    "$REMOTE_USER@{}" "rm -rf $REMOTE_DIR/*" \
    ::: $HOSTS

echo "Done."
