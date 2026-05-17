#!/usr/bin/env bash
# push_configs_to_setups.sh — Distribute MSW config files and SSH config to
# one or more setup machines via rsync over SSH.
#
# Usage:
#   ./push_configs_to_setups.sh --config-dir=<path> --setups=<name,...>
#                               [--ssh-config] [--user=<user>] [--dry-run]
#
# Options:
#   --config-dir=PATH    Local directory containing MSW config files (required)
#   --setups=LIST        Comma-separated list of setup hostnames (required)
#                        Example: setup1,setup2,setup3
#   --ssh-config         Also push ~/.ssh/config to each setup (optional)
#   --user=USER          Remote SSH user (default: current user)
#   --dry-run            Show rsync commands without executing them
#
# Example:
#   ./push_configs_to_setups.sh \
#       --config-dir=/mnt/maindata/CONFIG_FILES \
#       --setups=setup1,setup2,setup3 \
#       --ssh-config

set -euo pipefail

CONFIG_DIR=''
SETUPS_RAW=''
PUSH_SSH_CONFIG=false
REMOTE_USER="${USER:-pi}"
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --config-dir=*)  CONFIG_DIR="${arg#*=}" ;;
        --setups=*)      SETUPS_RAW="${arg#*=}" ;;
        --ssh-config)    PUSH_SSH_CONFIG=true ;;
        --user=*)        REMOTE_USER="${arg#*=}" ;;
        --dry-run)       DRY_RUN=true ;;
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

if [[ -z "$CONFIG_DIR" || -z "$SETUPS_RAW" ]]; then
    echo "Error: --config-dir and --setups are required." >&2
    echo "Run with --help for usage." >&2
    exit 1
fi

if [[ ! -d "$CONFIG_DIR" ]]; then
    echo "Error: config-dir not found: $CONFIG_DIR" >&2
    exit 1
fi

IFS=',' read -ra SETUPS <<< "$SETUPS_RAW"
RSYNC_OPTS=(-av --info=progress2)
$DRY_RUN && RSYNC_OPTS+=(--dry-run)

for setup in "${SETUPS[@]}"; do
    setup="${setup// /}"
    echo "======= $setup ======="
    rsync "${RSYNC_OPTS[@]}" "$CONFIG_DIR" "${REMOTE_USER}@${setup}:~/"
    if $PUSH_SSH_CONFIG; then
        rsync "${RSYNC_OPTS[@]}" ~/.ssh/config "${REMOTE_USER}@${setup}:~/.ssh/"
    fi
done

echo "Done."
