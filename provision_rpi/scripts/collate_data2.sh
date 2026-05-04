#!/usr/bin/env bash
# collate_data.sh — Multi-host rsync with live per-host progress display
#
# Usage:
#   ./collate_data.sh [group] [--source-dir=/path] [--target-dir=/path]
#                     [--identity=/path/to/key] [--dry-run]

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INVENTORY="$SCRIPT_DIR/../inventory.ini"
TARGET="/mnt/maindata/data/"
REMOTE_DIR="/data"
GROUP=''
IDENTITY=''
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --source-dir=*)  REMOTE_DIR="${arg#*=}" ;;
        --target-dir=*)  TARGET="${arg#*=}" ;;
        --identity=*)    IDENTITY="${arg#*=}" ;;
        --dry-run)       DRY_RUN=true ;;
        --*)             ;;
        *)               GROUP="$arg" ;;
    esac
done

# ── Colours ───────────────────────────────────────────────────────────────────
R='\033[0;31m'   G='\033[0;32m'   Y='\033[1;33m'
C='\033[0;36m'   W='\033[1;37m'   D='\033[2m'   M='\033[0;35m'   NC='\033[0m'

# ── Inventory parser ──────────────────────────────────────────────────────────
# Handles [group:vars] for ansible_user / ansible_ssh_private_key_file
# and [group:children] for nested group membership
parse_inventory() {
    local inv="$1"

    # Pass 1 — collect vars sections
    declare -gA group_vars=()
    local cur_var_group=''
    while IFS= read -r line; do
        line="${line%%#*}"; line="${line//[$'\r']}"
        [[ -z "${line// }" ]] && continue
        if [[ "$line" =~ ^\[([^]]+):vars\]$ ]]; then
            cur_var_group="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^\[.*\]$ ]]; then
            cur_var_group=''
        elif [[ -n "$cur_var_group" ]]; then
            group_vars["$cur_var_group"]+=" $line"
        fi
    done < "$inv"

    # Pass 2 — collect direct host members per group
    declare -A group_members=()
    local cur_group=''
    while IFS= read -r line; do
        line="${line%%#*}"; line="${line//[$'\r']}"
        [[ -z "${line// }" ]] && continue
        if [[ "$line" =~ ^\[([^]]+)\]$ ]]; then
            local hdr="${BASH_REMATCH[1]}"
            if [[ "$hdr" == *:children || "$hdr" == *:vars ]]; then
                cur_group=''
            else
                cur_group="$hdr"
                [[ -z "${group_members[$cur_group]+x}" ]] && group_members["$cur_group"]=''
            fi
        elif [[ -n "$cur_group" && "$line" =~ ansible_host= ]]; then
            local name ip
            name=$(awk '{print $1}' <<< "$line")
            ip=$(grep -oP 'ansible_host=\K\S+' <<< "$line")
            group_members["$cur_group"]+="$name=$ip "
        fi
    done < "$inv"

    # Pass 3 — resolve :children groups (two passes covers one level of nesting)
    declare -A children_map=()
    local cur_children=''
    while IFS= read -r line; do
        line="${line%%#*}"; line="${line//[$'\r']}"
        [[ -z "${line// }" ]] && continue
        if [[ "$line" =~ ^\[([^]]+):children\]$ ]]; then
            cur_children="${BASH_REMATCH[1]}"
            [[ -z "${children_map[$cur_children]+x}" ]] && children_map["$cur_children"]=''
        elif [[ "$line" =~ ^\[.*\]$ ]]; then
            cur_children=''
        elif [[ -n "$cur_children" ]]; then
            local child="${line// /}"
            [[ -n "$child" ]] && children_map["$cur_children"]+="$child "
        fi
    done < "$inv"

    for parent in "${!children_map[@]}"; do
        for child in ${children_map[$parent]:-}; do
            group_members["$parent"]+="${group_members[$child]:-} "
        done
    done
    # second pass for grandchildren
    for parent in "${!children_map[@]}"; do
        for child in ${children_map[$parent]:-}; do
            group_members["$parent"]+="${group_members[$child]:-} "
        done
    done

    # Select hosts
    local raw_members=''
    if [[ -n "$GROUP" ]]; then
        raw_members="${group_members[$GROUP]:-}"
        [[ -z "$raw_members" ]] && {
            printf "${R}Group '%s' not found in %s${NC}\n" "$GROUP" "$inv"; exit 1
        }
    else
        for g in "${!group_members[@]}"; do raw_members+="${group_members[$g]} "; done
    fi

    # Deduplicate
    declare -gA _seen=()
    declare -ga LABELS=() IPS=()
    for entry in $raw_members; do
        local name="${entry%%=*}" ip="${entry#*=}"
        [[ -z "$name" || -z "$ip" ]] && continue
        [[ -n "${_seen[$name]+x}" ]] && continue
        _seen["$name"]=1
        LABELS+=("$name"); IPS+=("$ip")
    done

    # Resolve ansible_user — walk: requested group → rpis → all → default
    declare -g REMOTE_USER='pi'
    for gname in "${GROUP:-rpis}" rpis all; do
        local v="${group_vars[$gname]:-}"
        if [[ "$v" =~ ansible_user=([^[:space:]]+) ]]; then
            REMOTE_USER="${BASH_REMATCH[1]}"; break
        fi
    done

    # Resolve SSH key — inventory first, then common defaults
    if [[ -z "$IDENTITY" ]]; then
        for gname in "${GROUP:-rpis}" rpis all; do
            local v="${group_vars[$gname]:-}"
            if [[ "$v" =~ ansible_ssh_private_key_file=([^[:space:]]+) ]]; then
                IDENTITY="${BASH_REMATCH[1]}"; break
            fi
        done
    fi
    if [[ -z "$IDENTITY" ]]; then
        for k in ~/.ssh/id_ed25519 ~/.ssh/id_rsa ~/.ssh/id_ecdsa; do
            [[ -f "$k" ]] && { IDENTITY="$k"; break; }
        done
    fi
}

parse_inventory "$INVENTORY"

N=${#LABELS[@]}
[[ $N -eq 0 ]] && { echo "No valid hosts found"; exit 1; }

SSH_OPTS="-o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=10"
[[ -n "$IDENTITY" ]] && SSH_OPTS+=" -i $IDENTITY"

# ── State directory ───────────────────────────────────────────────────────────
STDIR=$(mktemp -d)
cleanup() { tput cnorm 2>/dev/null || true; rm -rf "$STDIR"; }
trap cleanup EXIT INT TERM

for i in $(seq 0 $((N-1))); do
    printf 'waiting' > "$STDIR/s$i"
    : > "$STDIR/p$i"; : > "$STDIR/f$i"; : > "$STDIR/err$i"
done

# ── Helpers ───────────────────────────────────────────────────────────────────
LW=6
for l in "${LABELS[@]}"; do [[ ${#l} -gt $LW ]] && LW=${#l}; done

bar() {
    local p=${1:-0} w=24 s='' f
    f=$(( p * w / 100 ))
    for ((i=0; i<w; i++)); do
        if   ((i < f));            then s+='='
        elif ((i == f && p < 100)); then s+='>'
        else                            s+=' '
        fi
    done
    printf '[%s]' "$s"
}

fmt_bytes() { numfmt --to=iec-i --suffix=B "${1//,/}" 2>/dev/null || printf '%s B' "${1//,/}"; }

# ─────────────────────────────────────────────────────────────────────────────
# DRY-RUN path
# ─────────────────────────────────────────────────────────────────────────────
if $DRY_RUN; then
    printf "${M}DRY RUN${NC}  ${W}COLLATE DATA${NC}  "
    printf "${D}%d host(s)  %s@…:%s${NC}\n" "$N" "$REMOTE_USER" "$REMOTE_DIR"
    [[ -n "$IDENTITY" ]] && printf "${D}SSH key: %s${NC}\n" "$IDENTITY"
    printf '\n'
    for ((i=0; i<N; i++)); do printf '\n'; done

    dry_worker() {
        local idx=$1 ip=$2 rc=0
        printf 'running' > "$STDIR/s$idx"

        local out
        out=$(rsync -a --dry-run --stats \
            -e "ssh $SSH_OPTS" \
            "$REMOTE_USER@$ip:$REMOTE_DIR/" "$TARGET" \
            --exclude='.git' --exclude='__pycache__' \
            --exclude='.idea' --exclude='tests' --exclude='*.egg-info' \
            2>"$STDIR/err$idx") || rc=$?

        if [[ $rc -eq 0 ]]; then
            local tcount=0 tbytes=0 fcount=0 fbytes=0
            while IFS= read -r line; do
                [[ "$line" =~ ^Number\ of\ regular\ files\ transferred:\ +([0-9,]+) ]] \
                    && tcount="${BASH_REMATCH[1]//,/}"
                [[ "$line" =~ ^Total\ transferred\ file\ size:\ +([0-9,]+) ]] \
                    && tbytes="${BASH_REMATCH[1]//,/}"
                [[ "$line" =~ ^Number\ of\ files:\ +([0-9,]+) ]] \
                    && fcount="${BASH_REMATCH[1]//,/}"
                [[ "$line" =~ ^Total\ file\ size:\ +([0-9,]+) ]] \
                    && fbytes="${BASH_REMATCH[1]//,/}"
            done <<< "$out"
            printf '%s|%s|%s|%s|%s|%s' \
                "$tcount" "$(fmt_bytes "$tbytes")" "$tbytes" \
                "$fcount" "$(fmt_bytes "$fbytes")" "$fbytes" \
                > "$STDIR/f$idx"
            printf 'done' > "$STDIR/s$idx"
        else
            printf 'failed:%d' "$rc" > "$STDIR/s$idx"
        fi
    }

    for i in $(seq 0 $((N-1))); do dry_worker "$i" "${IPS[$i]}" & done

    spin=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
    tick=0
    tput civis 2>/dev/null || true

    while true; do
        printf "\033[%dA" "$N"
        for i in $(seq 0 $((N-1))); do
            label="${LABELS[$i]}"
            state=$(< "$STDIR/s$i")
            printf '\033[2K\r'
            printf "${W}%-*s${NC}  " "$LW" "$label"
            case "$state" in
                waiting)
                    printf "${D}waiting…${NC}" ;;
                running)
                    printf "${C}${spin[$((tick % 10))]} checking…${NC}" ;;
                done)
                    IFS='|' read -r tcount tbytes _ fcount fbytes _ < "$STDIR/f$i"
                    if [[ "$tcount" == "0" ]]; then
                        printf "${D}nothing to copy  (all %s in %s files up to date)${NC}" \
                            "$fbytes" "$fcount"
                    else
                        printf "${G}%6s files  ${W}%10s${NC}${D} to copy  " "$tcount" "$tbytes"
                        printf "(%s total across %s files)${NC}" "$fbytes" "$fcount"
                    fi
                    ;;
                failed:*)
                    errcode="${state#failed:}"
                    errmsg=$(head -1 "$STDIR/err$i" 2>/dev/null | sed 's/^[^:]*: //' || true)
                    printf "${R}✗  exit %s  %s${NC}" "$errcode" "$errmsg" ;;
            esac
            printf '\n'
        done

        running=0
        for i in $(seq 0 $((N-1))); do
            s=$(< "$STDIR/s$i")
            [[ "$s" == waiting || "$s" == running ]] && running=$((running+1))
        done
        [[ $running -eq 0 ]] && break
        tick=$((tick+1)); sleep 0.1
    done
    wait

    # ── Dry-run summary table ─────────────────────────────────────────────────
    printf '\n'
    printf "${D}%-*s  %7s  %12s  %7s  %12s${NC}\n" \
        "$LW" "HOST" "# FILES" "TO COPY" "# TOTAL" "TOTAL SIZE"
    printf "${D}%s${NC}\n" "$(printf '─%.0s' $(seq 1 $((LW + 46))))"

    total_tcount=0; total_tbytes=0; total_fcount=0; nfail=0
    for i in $(seq 0 $((N-1))); do
        state=$(< "$STDIR/s$i")
        if [[ "$state" == done ]]; then
            IFS='|' read -r tcount tbytes tbytes_raw fcount fbytes fbytes_raw < "$STDIR/f$i"
            printf "%-*s  %7s  %12s  %7s  %12s\n" \
                "$LW" "${LABELS[$i]}" "$tcount" "$tbytes" "$fcount" "$fbytes"
            total_tcount=$((total_tcount + tcount))
            total_tbytes=$((total_tbytes + tbytes_raw))
            total_fcount=$((total_fcount + fcount))
        else
            printf "${R}%-*s  ✗  %s${NC}\n" "$LW" "${LABELS[$i]}" "${state#failed:}"
            nfail=$((nfail+1))
        fi
    done

    printf "${D}%s${NC}\n" "$(printf '─%.0s' $(seq 1 $((LW + 46))))"
    printf "${W}%-*s  %7s  %12s${NC}\n" \
        "$LW" "TOTAL" "$total_tcount" "$(fmt_bytes "$total_tbytes")"
    [[ $nfail -gt 0 ]] && printf "${R}%d host(s) failed (check SSH/key above)${NC}\n" "$nfail"
    exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# LIVE SYNC path
# ─────────────────────────────────────────────────────────────────────────────
printf "${W}COLLATE DATA${NC}  ${D}%d host(s)  %s@…:%s  →  %s${NC}\n" \
    "$N" "$REMOTE_USER" "$REMOTE_DIR" "$TARGET"
[[ -n "$IDENTITY" ]] && printf "${D}SSH key: %s${NC}\n" "$IDENTITY"
printf '\n'
printf "${D}%-*s  %-26s  %4s  %-11s  %s${NC}\n" \
    "$LW" "HOST" "PROGRESS" "PCT" "SPEED" "ETA"
printf "${D}%s${NC}\n" "$(printf '─%.0s' $(seq 1 $((LW + 60))))"
for ((i=0; i<N; i++)); do printf '\n'; done

tput civis 2>/dev/null || true

run_rsync() {
    local idx=$1 ip=$2 rc=0 t0
    t0=$(date +%s)
    printf 'running' > "$STDIR/s$idx"
    set +e
    rsync -a --no-inc-recursive \
        --info=progress2 \
        -e "ssh $SSH_OPTS" \
        "$REMOTE_USER@$ip:$REMOTE_DIR/" "$TARGET" \
        --exclude='.git' --exclude='__pycache__' \
        --exclude='.idea' --exclude='tests' --exclude='*.egg-info' \
        2>"$STDIR/err$idx" \
      | tr '\r' '\n' \
      | grep --line-buffered '%' \
      | while IFS= read -r line; do printf '%s' "$line" > "$STDIR/p$idx"; done
    rc=${PIPESTATUS[0]}
    set -e

    local elapsed=$(( $(date +%s) - t0 ))
    if [[ $rc -eq 0 ]]; then
        local last bytes=''
        last=$(< "$STDIR/p$idx")
        [[ "$last" =~ ^[[:space:]]*([0-9,]+) ]] && bytes=$(fmt_bytes "${BASH_REMATCH[1]//,/}")
        printf '%s in %dm%02ds' "$bytes" "$((elapsed/60))" "$((elapsed%60))" > "$STDIR/f$idx"
        printf 'done' > "$STDIR/s$idx"
    else
        printf 'failed:%d' "$rc" > "$STDIR/s$idx"
    fi
}

for i in $(seq 0 $((N-1))); do run_rsync "$i" "${IPS[$i]}" & done

render_all() {
    local i label state pct speed eta prog
    for i in $(seq 0 $((N-1))); do
        label="${LABELS[$i]}"; state=$(< "$STDIR/s$i"); prog=$(< "$STDIR/p$i")
        pct=0; speed=''; eta=''
        [[ "$prog" =~ ([0-9]+)%              ]] && pct="${BASH_REMATCH[1]}"
        [[ "$prog" =~ ([0-9.]+[KMGkmg]i?B/s) ]] && speed="${BASH_REMATCH[1]}"
        [[ "$prog" =~ ([0-9]+:[0-9]+:[0-9]+) ]] && eta="${BASH_REMATCH[1]}"
        printf '\033[2K\r'
        printf "${W}%-*s${NC}  " "$LW" "$label"
        case "$state" in
            waiting)
                printf "${D}%s  waiting…${NC}" "$(bar 0)" ;;
            running)
                printf "${Y}%s${NC}" "$(bar "$pct")"
                printf "  ${C}%3s%%${NC}  ${W}%-11s${NC}" "$pct" "${speed:-          }"
                [[ -n "$eta" ]] && printf "${D}eta %-8s${NC}" "$eta" ;;
            done)
                printf "${G}%s  100%%  ✓  %s${NC}" "$(bar 100)" "$(< "$STDIR/f$i")" ;;
            failed:*)
                local errcode="${state#failed:}"
                local errmsg; errmsg=$(head -1 "$STDIR/err$i" 2>/dev/null | sed 's/^[^:]*: //' || true)
                printf "${R}%s  ✗  exit %s  %s${NC}" "$(bar "$pct")" "$errcode" "$errmsg" ;;
        esac
        printf '\n'
    done
}

while true; do
    printf "\033[%dA" "$N"
    render_all
    running=0
    for i in $(seq 0 $((N-1))); do
        s=$(< "$STDIR/s$i"); [[ "$s" == waiting || "$s" == running ]] && running=$((running+1))
    done
    [[ $running -eq 0 ]] && break
    sleep 0.15
done
wait

printf '\n'
NFAIL=0
for i in $(seq 0 $((N-1))); do
    s=$(< "$STDIR/s$i"); [[ "$s" == failed:* ]] && NFAIL=$((NFAIL+1))
done
if [[ $NFAIL -gt 0 ]]; then
    printf "${R}%d of %d transfer(s) failed.${NC}\n" "$NFAIL" "$N"
    exit 1
else
    printf "${G}All %d transfer(s) complete.${NC}\n" "$N"
fi
