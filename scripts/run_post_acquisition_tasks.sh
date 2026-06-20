#!/usr/bin/env bash
# run_post_acquisition_tasks.sh — Orchestrate post-acquisition data pipeline
# for a single rig session.
#
# Steps (each is optional via flags):
#   1. Sync local ~/data/ to the central data store
#   2. Collate data from RPi cameras  (requires provision_rpi/collate_data2.sh)
#   3. Collate data from setup machines  (requires provision_rpi/collate_data2.sh)
#   4. Convert .h264 video files to .mp4  (requires provision_rpi/h264_to_mp4.sh)
#   5. Clean MSW noise events from .msw.csv files  (clean_msw_files.sh)
#   6. Upload data to remote server  (requires provision_rpi/upload_to_server.sh)
#
# Usage:
#   ./run_post_acquisition_tasks.sh \
#       --local-data=<path>     \
#       --central-data=<path>   \
#       --provision-scripts=<path>  \
#       [--rpi-group=<group>]   \
#       [--setup-group=<group>] \
#       [--target-dir=<path>]   \
#       [--skip-upload]         \
#       [--skip-rpi]            \
#       [--skip-setups]         \
#       [--skip-h264]           \
#       [--skip-msw-clean]      \
#       [--dry-run]
#
# Options:
#   --local-data=PATH        Local data dir to sync to central (default: ~/data)
#   --central-data=PATH      Central data directory (required)
#   --provision-scripts=PATH Path to provision_rpi/scripts/ directory (required)
#   --rpi-group=GROUP        Ansible inventory group for RPi cameras (default: rpis)
#   --setup-group=GROUP      Ansible inventory group for setup machines
#   --target-dir=PATH        Remote upload destination (default: $MSW_UPLOAD_TARGET or /data/)
#   --skip-upload            Skip remote upload step
#   --skip-rpi               Skip RPi data collation
#   --skip-setups            Skip setup machine data collation
#   --skip-h264              Skip h264 → mp4 conversion
#   --skip-msw-clean         Skip MSW noise-event cleanup
#   --dry-run                Pass --dry-run to all sub-scripts

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_DATA="${HOME}/data"
CENTRAL_DATA=''
PROVISION_SCRIPTS=''
RPI_GROUP='rpis'
SETUP_GROUP=''
TARGET_DIR="${MSW_UPLOAD_TARGET:-/data/}"
SKIP_UPLOAD=false
SKIP_RPI=false
SKIP_SETUPS=false
SKIP_H264=false
SKIP_MSW_CLEAN=false
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --local-data=*)        LOCAL_DATA="${arg#*=}" ;;
        --central-data=*)      CENTRAL_DATA="${arg#*=}" ;;
        --provision-scripts=*) PROVISION_SCRIPTS="${arg#*=}" ;;
        --rpi-group=*)         RPI_GROUP="${arg#*=}" ;;
        --setup-group=*)       SETUP_GROUP="${arg#*=}" ;;
        --target-dir=*)        TARGET_DIR="${arg#*=}" ;;
        --skip-upload)         SKIP_UPLOAD=true ;;
        --skip-rpi)            SKIP_RPI=true ;;
        --skip-setups)         SKIP_SETUPS=true ;;
        --skip-h264)           SKIP_H264=true ;;
        --skip-msw-clean)      SKIP_MSW_CLEAN=true ;;
        --dry-run)             DRY_RUN=true ;;
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

if [[ -z "$CENTRAL_DATA" || -z "$PROVISION_SCRIPTS" ]]; then
    echo "Error: --central-data and --provision-scripts are required." >&2
    echo "Run with --help for usage." >&2
    exit 1
fi

DRY_FLAG=''
$DRY_RUN && DRY_FLAG='--dry-run'

# ── Step 1: local data → central ─────────────────────────────────────────────
echo "=== Step 1: Sync local data → central ==="
RSYNC_OPTS=(-a --info=progress2)
$DRY_RUN && RSYNC_OPTS+=(--dry-run)
rsync "${RSYNC_OPTS[@]}" "${LOCAL_DATA}/" "${CENTRAL_DATA}/"

# ── Step 2: RPi camera data → central ────────────────────────────────────────
if ! $SKIP_RPI; then
    echo "=== Step 2: Collate RPi camera data (group: $RPI_GROUP) ==="
    bash "${PROVISION_SCRIPTS}/collate_data2.sh" \
        "$RPI_GROUP" \
        --target-dir="$CENTRAL_DATA" \
        $DRY_FLAG
fi

# ── Step 3: Setup machine data → central ─────────────────────────────────────
if ! $SKIP_SETUPS && [[ -n "$SETUP_GROUP" ]]; then
    echo "=== Step 3: Collate setup machine data (group: $SETUP_GROUP) ==="
    bash "${PROVISION_SCRIPTS}/collate_data2.sh" \
        "$SETUP_GROUP" \
        --target-dir="$CENTRAL_DATA" \
        $DRY_FLAG
fi

# ── Step 4: h264 → mp4 ───────────────────────────────────────────────────────
if ! $SKIP_H264; then
    echo "=== Step 4: Convert .h264 → .mp4 ==="
    bash "${PROVISION_SCRIPTS}/h264_to_mp4.sh" \
        --source-dir="$CENTRAL_DATA" \
        $DRY_FLAG 2>/dev/null || \
    bash "${PROVISION_SCRIPTS}/h264_to_mp4.sh" \
        --source-dir="$CENTRAL_DATA"
fi

# ── Step 5: MSW noise-event cleanup ──────────────────────────────────────────
if ! $SKIP_MSW_CLEAN; then
    echo "=== Step 5: Clean MSW noise events ==="
    bash "${SCRIPT_DIR}/clean_msw_files.sh" \
        --data-dir="$CENTRAL_DATA" \
        $DRY_FLAG
fi

# ── Step 6: Upload to remote server ──────────────────────────────────────────
if ! $SKIP_UPLOAD; then
    echo "=== Step 6: Upload to remote server ==="
    bash "${PROVISION_SCRIPTS}/upload_to_server.sh" \
        --source-dir="$CENTRAL_DATA" \
        --target-dir="$TARGET_DIR" \
        $DRY_FLAG
fi

echo ""
echo "Post-acquisition pipeline complete."
