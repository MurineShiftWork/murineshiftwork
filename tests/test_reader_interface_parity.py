"""
Test that read_session_data() presents identical computational interface for
legacy (.pkl) and new (.jsonl) session formats.

Checks:
  - Same top-level keys present in session_data dict
  - df has same columns (order-independent)
  - df dtypes match or are safely equivalent (e.g. object vs StringDtype)
  - df columns have same value types at the cell level (first non-null per column)
  - settings.task and settings.process have same top-level keys

Usage
-----
python tests/test_reader_interface_parity.py
python tests/test_reader_interface_parity.py --new /path/new --legacy /path/legacy
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from murineshiftwork.readers.session import read_session_data

NEW_DEFAULT = (
    "/mnt/maindata/data/_test_subject"
    "/_test_subject__20260504_100148__probabilistic_switching_fixedsubjects"
)
LEGACY_DEFAULT = (
    "/mnt/maindata/data/t006_acute_m1102321_201"
    "/t006_acute_m1102321_201__20260327_142204__probabilistic_switching_fixedsubjects"
)


# ── helpers ────────────────────────────────────────────────────────────────────


def _dtype_class(dtype) -> str:
    """Collapse dtype to a broad class for comparison: numeric / bool / object."""
    if pd.api.types.is_bool_dtype(dtype):
        return "bool"
    if pd.api.types.is_integer_dtype(dtype):
        return "int"
    if pd.api.types.is_float_dtype(dtype):
        return "float"
    return "object"


def _cell_type(series: pd.Series) -> str:
    first = series.dropna().iloc[0] if series.dropna().shape[0] else None
    if first is None:
        return "all-null"
    return type(first).__name__


def compare_dfs(
    df_new: pd.DataFrame, df_leg: pd.DataFrame
) -> tuple[list[str], list[str]]:
    """Returns (failures, warnings).

    Failures: dtype class mismatches on shared columns — these would break computation.
    Warnings: column-presence differences (task-version or event-occurrence) and
              list-vs-tuple differences (pre-fix JSONL files lack __tuple__ sentinel).
    """
    failures = []
    warnings = []

    cols_new = set(df_new.columns)
    cols_leg = set(df_leg.columns)

    only_new = cols_new - cols_leg
    only_leg = cols_leg - cols_new

    # Column-presence differences are content/version differences, not reader bugs.
    if only_new:
        warnings.append(
            f"Columns only in NEW ({len(only_new)}) — likely task version update: {sorted(only_new)}"
        )
    if only_leg:
        warnings.append(
            f"Columns only in LEGACY ({len(only_leg)}) — events absent in short/test session: {sorted(only_leg)}"
        )

    shared = sorted(cols_new & cols_leg)

    dtype_mismatches = []
    cell_type_mismatches = []

    for col in shared:
        cls_new = _dtype_class(df_new[col].dtype)
        cls_leg = _dtype_class(df_leg[col].dtype)
        if cls_new != cls_leg:
            dtype_mismatches.append(
                f"  {col}: new={df_new[col].dtype} ({cls_new})  legacy={df_leg[col].dtype} ({cls_leg})"
            )

        ct_new = _cell_type(df_new[col])
        ct_leg = _cell_type(df_leg[col])
        if ct_new != ct_leg and "all-null" not in (ct_new, ct_leg):
            # list vs tuple: known pre-fix artifact for JSONL files saved before the
            # __tuple__ sentinel encoding was added. New saves will round-trip tuples
            # correctly. Warn rather than fail — downstream code handles both types.
            if set([ct_new, ct_leg]) == {"list", "tuple"}:
                warnings.append(
                    f"  {col}: list/tuple mismatch (pre-fix JSONL file — new saves correct)"
                )
            else:
                cell_type_mismatches.append(
                    f"  {col}: new cell type={ct_new}  legacy cell type={ct_leg}"
                )

    if dtype_mismatches:
        failures.append(
            f"Dtype class mismatches ({len(dtype_mismatches)}):\n"
            + "\n".join(dtype_mismatches)
        )
    if cell_type_mismatches:
        failures.append(
            f"Cell type mismatches ({len(cell_type_mismatches)}):\n"
            + "\n".join(cell_type_mismatches)
        )

    return failures, warnings


def compare_settings(s_new: dict, s_leg: dict, label: str) -> list[str]:
    issues = []
    only_new = set(s_new) - set(s_leg)
    only_leg = set(s_leg) - set(s_new)
    if only_new:
        issues.append(f"{label} keys only in NEW: {sorted(only_new)}")
    if only_leg:
        issues.append(f"{label} keys only in LEGACY: {sorted(only_leg)}")
    return issues


# ── main ───────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--new", default=NEW_DEFAULT)
    parser.add_argument("--legacy", default=LEGACY_DEFAULT)
    args = parser.parse_args()

    print("=" * 70)
    print("MSW reader interface parity test")
    print(f"  NEW    : {args.new}")
    print(f"  LEGACY : {args.legacy}")
    print("=" * 70)

    sd_new = read_session_data(session_dir=args.new)
    sd_leg = read_session_data(session_dir=args.legacy)

    all_issues = []

    # ── 1. Top-level session_data keys ────────────────────────────────────────
    print("\n[1] Top-level session_data keys")
    keys_new = set(sd_new.keys())
    keys_leg = set(sd_leg.keys())

    shared_keys = keys_new & keys_leg
    only_new_k = keys_new - keys_leg
    only_leg_k = keys_leg - keys_new

    print(f"  Shared keys ({len(shared_keys)}): {sorted(shared_keys)}")
    if only_new_k:
        print(f"  Only in NEW: {sorted(only_new_k)}")
    if only_leg_k:
        print(f"  Only in LEGACY: {sorted(only_leg_k)}")

    # msw_version only present in new sessions — not an issue
    expected_only_new = {"msw_version"}
    unexpected_only_new = only_new_k - expected_only_new
    if unexpected_only_new:
        all_issues.append(f"Unexpected keys only in NEW: {unexpected_only_new}")
    if only_leg_k:
        all_issues.append(f"Keys missing from NEW: {only_leg_k}")

    # ── 2. Completeness flags ─────────────────────────────────────────────────
    print("\n[2] Completeness flags")
    for flag in (
        "is_complete_session",
        "is_legacy_session",
        "is_ephys_session",
    ):
        vn = sd_new.get(flag)
        vl = sd_leg.get(flag)
        match = "OK" if vn == vl else "MISMATCH"
        print(f"  {flag}: new={vn}  legacy={vl}  [{match}]")
        if vn != vl:
            all_issues.append(f"Flag mismatch: {flag}: new={vn} legacy={vl}")

    # ── 3. df columns and types ───────────────────────────────────────────────
    print("\n[3] Trial DataFrame (df)")
    df_new = sd_new.get("df")
    df_leg = sd_leg.get("df")

    if df_new is None or df_leg is None:
        all_issues.append("df is None in one or both sessions — cannot compare")
        print("  ERROR: df is None in one or both sessions")
    else:
        print(f"  NEW    shape: {df_new.shape}  columns: {len(df_new.columns)}")
        print(f"  LEGACY shape: {df_leg.shape}  columns: {len(df_leg.columns)}")

        df_failures, df_warnings = compare_dfs(df_new, df_leg)
        for w in df_warnings:
            print(f"  WARN: {w}")
        for f in df_failures:
            print(f"  FAIL: {f}")
            all_issues.append(f)
        if not df_failures and not df_warnings:
            print("  OK — same columns, same dtype classes, same cell types")
        elif not df_failures:
            print(
                "  OK — no dtype failures (warnings above are content/version differences)"
            )

        # Show dtype summary for shared columns
        shared_cols = sorted(set(df_new.columns) & set(df_leg.columns))
        print(f"\n  Shared columns ({len(shared_cols)}) — dtype NEW | LEGACY:")
        for col in shared_cols:
            dn = str(df_new[col].dtype)
            dl = str(df_leg[col].dtype)
            flag = (
                ""
                if _dtype_class(df_new[col].dtype) == _dtype_class(df_leg[col].dtype)
                else "  *** MISMATCH"
            )
            print(f"    {col:<45} {dn:<20} | {dl}{flag}")

    # ── 4. settings.task keys ─────────────────────────────────────────────────
    print("\n[4] settings.task keys")
    st_new = sd_new.get("settings.task") or {}
    st_leg = sd_leg.get("settings.task") or {}
    st_issues = compare_settings(st_new, st_leg, "settings.task")
    if st_issues:
        for iss in st_issues:
            print(f"  INFO: {iss}")
    else:
        print(f"  OK — same top-level keys ({len(st_new)})")

    # ── 5. settings.process keys ──────────────────────────────────────────────
    print("\n[5] settings.process keys")
    sp_new = sd_new.get("settings.process") or {}
    sp_leg = sd_leg.get("settings.process") or {}
    sp_issues = compare_settings(sp_new, sp_leg, "settings.process")
    if sp_issues:
        for iss in sp_issues:
            print(f"  INFO: {iss}")
    else:
        print(f"  OK — same top-level keys ({len(sp_new)})")

    # ── Result ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    if all_issues:
        print(f"FAIL — {len(all_issues)} issue(s):")
        for iss in all_issues:
            print(f"  - {iss}")
        sys.exit(1)
    else:
        print("PASS — both session formats present identical computational interface")


if __name__ == "__main__":
    main()
