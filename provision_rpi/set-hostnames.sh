#!/usr/bin/env bash
# Set hostname on every Pi in inventory.ini via SSH.
# Hostname is taken from the inventory name column (e.g. rpi-121) which already
# encodes the last IP octet, so no guessing is needed.
# Requires SSH key auth to be in place (run ssh-copy-id-all.sh first).
# Usage:  ./set-hostnames.sh [user]

set -euo pipefail

USER=${1:-pi}
INVENTORY="$(dirname "$0")/inventory.ini"

# Parse lines of the form:   rpi-121 ansible_host=192.168.100.121
while read -r hostname ip; do
    echo ">>> ${hostname}  (${ip})"
    ssh -n \
        -o StrictHostKeyChecking=yes \
        -o ConnectTimeout=5 \
        "${USER}@${ip}" \
        "echo 'preserve_hostname: true' | sudo tee /etc/cloud/cloud.cfg.d/99-preserve-hostname.cfg && echo '${hostname}' | sudo tee /etc/hostname && echo 'hostname set to ${hostname}' && sudo reboot now" || true
done < <(grep -E '^\s*rpi-[0-9]+\s+ansible_host=' "$INVENTORY" \
         | awk '{match($2, /ansible_host=([0-9.]+)/, a); print $1, a[1]}')

echo "Done."
