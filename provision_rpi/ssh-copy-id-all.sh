#!/usr/bin/env bash
# Copy SSH public key to all hosts listed in inventory.ini.
# Prompts for the password once, then applies it to every host via sshpass.
# Usage:  ./ssh-copy-id-all.sh [user]
# Default user: pi

set -euo pipefail

USER=${1:-pi}
INVENTORY="$(dirname "$0")/inventory.ini"

# Ensure sshpass is available
if ! command -v sshpass &>/dev/null; then
    echo "sshpass not found — installing..."
    sudo apt-get install -y sshpass
fi

# Prompt once, silently
read -rsp "Password for ${USER}@<all hosts>: " PASSWORD
echo

# Extract ansible_host IPs from inventory
HOSTS=$(grep -oP 'ansible_host=\K[\d.]+' "$INVENTORY")

for host in $HOSTS; do
    echo ">>> ${USER}@${host}"
    # Remove ALL existing entries for this IP (handles duplicates of any key type).
    # ssh-keygen -R removes them but leaves a .old backup; we also scrub that noise.
    ssh-keygen -f "${HOME}/.ssh/known_hosts" -R "$host" &>/dev/null || true
    # Remove the backup file ssh-keygen leaves behind
    rm -f "${HOME}/.ssh/known_hosts.old"
    # Fetch the current host key and write exactly one clean entry
    ssh-keyscan -H "$host" 2>/dev/null >> "${HOME}/.ssh/known_hosts"
    sshpass -p "$PASSWORD" ssh-copy-id -o StrictHostKeyChecking=yes "${USER}@${host}"
done

echo "Done."
