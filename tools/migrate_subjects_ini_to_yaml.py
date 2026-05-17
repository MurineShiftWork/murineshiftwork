"""Migrate subject.settings (configobj INI) → per-subject YAML files.

Usage:
    python tools/migrate_subjects_ini_to_yaml.py

Reads:   /mnt/maindata/CONFIG_FILES/subject.settings
Writes:  /mnt/maindata/msw_configs/subjects/{subject_name}.yaml

Rules:
- Each top-level [section] is a subject.
- Top-level scalar fields (project, experiment, comment, aliases) are mapped
  directly; all others are ignored (they are not part of SubjectConfig).
- aliases is stored as a string in the INI → converted to a one-element list.
- Nested [[task_name]] sections → task_overrides[task_name] = {key: value}.
  Values are parsed with ast.literal_eval; on failure they are kept as strings.
- The _test_subject section is skipped (written separately as _test_subject.yaml).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import yaml
from configobj import ConfigObj

INI_PATH = Path("/mnt/maindata/CONFIG_FILES/subject.settings")
OUT_DIR = Path("/mnt/maindata/msw_configs/subjects")
SKIP_SECTIONS = {"_test_subject"}

# Top-level scalar fields we recognise as SubjectConfig fields
SUBJECT_SCALAR_FIELDS = {
    "project",
    "experiment",
    "comment",
    "aliases",
    "registered",
}


def parse_value(raw):
    """Try to parse a Python literal; fall back to the raw string.

    configobj splits comma-separated values into a list of strings.
    When raw is a list, rejoin with ", " before parsing.
    """
    if isinstance(raw, list):
        raw = ", ".join(raw)
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return raw


def convert_value(v):
    """Recursively convert tuples → lists so YAML serialises cleanly."""
    if isinstance(v, tuple):
        return [convert_value(i) for i in v]
    if isinstance(v, list):
        return [convert_value(i) for i in v]
    return v


def build_subject_dict(name: str, section) -> dict:
    """Build the SubjectConfig dict from a configobj section."""
    subject: dict = {
        "name": name,
        "registered": "",
        "project": "",
        "experiment": "",
        "comment": "",
        "aliases": [],
        "task_overrides": {},
    }

    for key, value in section.items():
        if isinstance(value, dict):
            # Nested section → task_overrides entry
            task_overrides: dict[str, object] = {}
            for k, v in value.items():
                parsed = parse_value(v)
                task_overrides[k] = convert_value(parsed)
            subject["task_overrides"][key] = task_overrides
        elif key in SUBJECT_SCALAR_FIELDS:
            if key == "aliases":
                raw = (
                    value.strip('"').strip("'")
                    if isinstance(value, str)
                    else str(value)
                )
                subject["aliases"] = [raw] if raw else []
            else:
                # Strip surrounding quotes that configobj sometimes preserves
                cleaned = (
                    value.strip('"').strip("'")
                    if isinstance(value, str)
                    else str(value)
                )
                subject[key] = cleaned
        # Other unknown scalar keys at subject level are silently ignored

    return subject


def main() -> None:
    if not INI_PATH.exists():
        print(f"ERROR: INI file not found: {INI_PATH}", file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cfg = ConfigObj(str(INI_PATH), interpolation=False)

    written = 0
    for section_name, section_data in cfg.items():
        if section_name in SKIP_SECTIONS:
            print(f"  skip: {section_name}")
            continue

        subject_dict = build_subject_dict(section_name, section_data)

        out_path = OUT_DIR / f"{section_name}.yaml"
        with open(out_path, "w") as fh:
            yaml.dump(
                subject_dict,
                fh,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        print(f"  wrote: {out_path}")
        written += 1

    print(f"\nDone. {written} subject YAML file(s) written to {OUT_DIR}")


if __name__ == "__main__":
    main()
