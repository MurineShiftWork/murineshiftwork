import logging
from pathlib import Path

import yaml

from murineshiftwork.readers.files import (
    read_json,
    read_settings_py,
    read_trial_df,
)
from murineshiftwork.readers.namespace import (
    ARTIFACT_FORMAT_LEGACY,
    ARTIFACT_FORMAT_SEPARATE_JSON,
    ARTIFACT_FORMAT_SESSION_YAML,
    detect_session_format,
    test_is_legacy_format,
    test_is_recognized_msw_file,
)


def _msw_files_dict(session_dir: Path) -> dict[str, str]:
    """Return {artifact_key: filepath} for all recognised MSW files in session_dir.

    Non-MSW files (RCE camera files, Open Ephys record nodes, etc.) are present in
    the directory but are not included here and are not loaded. Those files belong to
    their respective packages; readers/ only handles the .msw.* file set.
    """
    files = [str(p) for p in session_dir.glob("*")]

    def _key(s: str) -> str:
        return s.split(".msw.")[-1].replace("msw", "").strip(".")

    return {_key(v): v for v in files if test_is_recognized_msw_file(v)}


def _attach_msw_version(data: dict, is_legacy: bool) -> None:
    """Set data["msw_version"] from settings.process or format fallback."""
    proc = data.get("settings.process", {}) or {}
    if "msw_version" in proc:
        data["msw_version"] = proc["msw_version"]
    elif is_legacy:
        data["msw_version"] = "legacy"
    else:
        data["msw_version"] = "< 1.0.0"


def _check_completeness(data: dict, is_legacy: bool) -> bool:
    required = ["df", "settings.task"]
    if not is_legacy:
        required.append("settings.process")
    for k in required:
        if k not in data:
            return False
    return data.get("df") is not None


# ---------------------------------------------------------------------------
# Per-format readers


def _read_session_yaml(session_dir: Path, fmt: dict) -> dict:
    """ARTIFACT_FORMAT_SESSION_YAML — single .msw.session.yaml (v2+)."""
    files = _msw_files_dict(session_dir)
    data: dict = {}

    for k, v in files.items():
        if k == "session.yaml" and ".msw." in v:
            payload = yaml.safe_load(Path(v).read_text()) or {}
            if payload.get("msw_format_version", 1) >= 2:
                if "process" in payload:
                    data["settings.process"] = payload["process"]
                if "task_settings" in payload:
                    data["settings.task"] = payload["task_settings"]
                if "stage" in payload:
                    data["settings.stage"] = payload["stage"]
        elif Path(k).name.endswith("pkl") or Path(k).name.endswith("jsonl"):
            data["df"] = read_trial_df(filepath=v)
        elif Path(k).name.endswith("csv"):
            pass  # pybpod CSV present but not loaded; use ttl_barcoder for alignment
        else:
            logging.debug("session_yaml reader: unrecognised key %r — %s", k, v)

    return data


def _read_separate_json(session_dir: Path, fmt: dict) -> dict:
    """ARTIFACT_FORMAT_SEPARATE_JSON — separate .msw.settings.*.json + df file."""
    files = _msw_files_dict(session_dir)
    data: dict = {}

    for k, v in files.items():
        if Path(k).name.endswith("csv"):
            pass  # pybpod CSV present but not loaded
        elif Path(k).name.endswith("pkl") or Path(k).name.endswith("jsonl"):
            data["df"] = read_trial_df(filepath=v)
        elif k.endswith("json") and ".msw." in v:
            data[k.replace(".json", "")] = read_json(file=v)
        else:
            logging.debug("separate_json reader: unrecognised key %r — %s", k, v)

    # legacy fallback: older separate-JSON sessions used different key names
    for k, v in files.items():
        if k.endswith("settings.json") and "settings.process" not in data:
            data["settings.process"] = read_json(v)
        elif k.endswith("settings") and "settings.task" not in data:
            data["settings.task"] = read_json(v)

    return data


def _read_legacy(session_dir: Path, fmt: dict) -> dict:
    """ARTIFACT_FORMAT_LEGACY — task_settings.py + switching.pkl/csv."""
    # legacy sessions: scan all files (no .msw. segment present)
    all_files = [str(p) for p in session_dir.glob("*")]
    data: dict = {}

    for v in all_files:
        name = Path(v).name
        if name == "task_settings.py" or name.endswith(".task_settings.py"):
            data["settings.task"] = read_settings_py(file=v)
        elif name.endswith(".pkl") or name.endswith("switching.pkl"):
            if "df" not in data:
                data["df"] = read_trial_df(filepath=v)
        elif name.endswith(".csv") or name.endswith("switching.csv"):
            pass  # pybpod CSV not loaded; was legacy raw Bpod event log

    return data


_READER_DISPATCH = {
    ARTIFACT_FORMAT_SESSION_YAML: _read_session_yaml,
    ARTIFACT_FORMAT_SEPARATE_JSON: _read_separate_json,
    ARTIFACT_FORMAT_LEGACY: _read_legacy,
}


# ---------------------------------------------------------------------------
# Public API


def read_session_data(session_dir=None):
    """Read session data, dispatching to the correct reader based on artifact format.

    Returns a dict with keys: df, settings.task, settings.process, settings.stage,
    msw_version, namespace_version, artifact_format, is_legacy_session,
    is_complete_session, is_ephys_session.
    """
    session_dir = Path(session_dir)
    assert session_dir.exists()

    fmt = detect_session_format(session_dir)
    artifact_format = fmt["artifact_format"]
    is_legacy = test_is_legacy_format(session_dir=session_dir)

    reader = _READER_DISPATCH.get(artifact_format)
    if reader is None:
        raise ValueError(
            f"No reader registered for artifact format {artifact_format!r}"
        )

    data = reader(session_dir, fmt)

    data["namespace_version"] = fmt["namespace_version"]
    data["artifact_format"] = artifact_format
    data["is_legacy_session"] = is_legacy
    _attach_msw_version(data, is_legacy)
    data["is_complete_session"] = _check_completeness(data, is_legacy)
    data["is_ephys_session"] = "settings.ephys" in data

    return data


if __name__ == "__main__":
    import murineshiftwork
    from murineshiftwork.logic.log import setup_logging

    setup_logging()

    BASE_PATH = Path(murineshiftwork.__path__[0]).parent / "tests"

    TEST_FILE_1 = (
        BASE_PATH
        / "_test_subject/_test_subject__20211004_191858__probabilistic_switching"
    )
    TEST_FILE_2 = (
        BASE_PATH
        / "sleep_lhb_c344986_m1097354__20210718_152153__probabilistic_switching"
    )
    TEST_FILE_3 = (
        BASE_PATH
        / "tab_npx_007_m1114799_LL_chrOn__20210928_120653__probabilistic_switching"
    )

    session_data = read_session_data(session_dir=TEST_FILE_1)
    print(" ")
