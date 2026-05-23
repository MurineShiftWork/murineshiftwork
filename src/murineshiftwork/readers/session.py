import logging
from pathlib import Path

import yaml

from murineshiftwork.readers.files import (
    read_json,
    read_pybpod_csv,
    read_settings_py,
    read_trial_df,
)
from murineshiftwork.readers.namespace import (
    test_is_legacy_format,
    test_is_recognized_msw_file,
)


def read_session_data(
    session_dir=None,
    load_raw=False,
    clean_port4_events=True,
    return_trial_structure_only=True,
):
    """Read session data for this acquisition package.

    Namespace:
        - current files all have a "*.msw.*" segment after the session name
        - legacy files differ:
            - task settings:    "task_settings.py"
            - df:               ".msw.pkl" or "switching.pkl"
            - csv:              ".msw.csv" or "switching.csv"

    Expected files:
        - Trial dataframe:      .msw.jsonl or .msw.df.jsonl (v2.0.0+), .msw.pkl or .msw.df.pkl (legacy)
        - Raw pybpod data:      .msw.csv or .csv [might be ambiguous with RCC files]
        - 2 settings files:     .msw.settings.[task|process].json

    :param session_dir: directory that contains session files
    :param load_raw: load raw CSV file
    :param clean_port4_events: remove events that occurred on Port4
    :param return_trial_structure_only: returns only trial structure events, no port events etc.
    :return:
    """
    session_dir = Path(session_dir)
    assert session_dir.exists()

    files_in_dir = [str(p) for p in session_dir.glob("*")]

    def _prepare_key(s=None):
        return s.split(".msw.")[-1].replace("msw", "").strip(".")

    session_files_dict = {
        _prepare_key(v): v for v in files_in_dir if test_is_recognized_msw_file(v)
    }
    is_legacy_session = test_is_legacy_format(session_dir=session_dir)

    session_data = {}
    session_data["is_legacy_session"] = is_legacy_session

    for k, v in session_files_dict.items():
        if Path(k).name.endswith("csv"):
            # Add key for session completeness, but might be empty if input load_raw=False
            session_data["raw"] = None
            if load_raw:
                session_data["raw"] = read_pybpod_csv(
                    filepath=v,
                    clean_events=clean_port4_events,
                    return_trial_structure_only=return_trial_structure_only,
                )

        elif Path(k).name.endswith("pkl") or Path(k).name.endswith("jsonl"):
            session_data["df"] = read_trial_df(filepath=v)

        elif k == "session.yaml" and ".msw." in v:
            # v2 format: single YAML with process + task_settings (+ optional stage)
            payload = yaml.safe_load(Path(v).read_text()) or {}
            if payload.get("msw_format_version", 1) >= 2:
                if "process" in payload:
                    session_data["settings.process"] = payload["process"]
                if "task_settings" in payload:
                    session_data["settings.task"] = payload["task_settings"]
                if "stage" in payload:
                    session_data["settings.stage"] = payload["stage"]

        elif k.endswith("json") and ".msw." in v:
            # v1 format: separate task & process JSON files
            session_data[k.replace(".json", "")] = read_json(file=v)

        elif Path(k).name == "task_settings.py" and is_legacy_session:
            session_data["settings.task"] = read_settings_py(file=v)

        else:
            logging.debug(f"Unrecognized file: {k} - {v}")

    # Check for legacy files
    for k, v in session_files_dict.items():
        if k.endswith("settings.json") and "settings.process" not in session_data:
            session_data["settings.process"] = read_json(v)

        elif k.endswith("settings") and "settings.task" not in session_data:
            session_data["settings.task"] = read_json(v)

    # Expose msw_version at top level — always set so callers can branch on it
    # without digging into settings.process.
    #   "legacy"  — very old format: task_settings.py, no process JSON
    #   "< 1.0.0" — process JSON exists but pre-version-tracking (before 2026-05-04)
    #   "x.y.z"   — version string written by TaskProcess.persist_settings()
    proc = session_data.get("settings.process", {}) or {}
    if "msw_version" in proc:
        session_data["msw_version"] = proc["msw_version"]
    elif is_legacy_session:
        session_data["msw_version"] = "legacy"
    else:
        session_data["msw_version"] = "< 1.0.0"

    # Check if session data is complete
    required_file_keys = ["raw", "df", "settings.task"]
    if not is_legacy_session:
        required_file_keys += ["settings.process"]

    is_complete_session = True
    for k in required_file_keys:
        if k not in session_data:
            is_complete_session = False

    if "raw" in session_data and session_data["raw"] is None and load_raw:
        is_complete_session = False

    if "df" in session_data and session_data["df"] is None:
        is_complete_session = False
        # FIXME: add option to recover trial start times from legacy acquisition from raw CSV

    session_data["is_complete_session"] = is_complete_session

    # Check if is ephys session at top level
    session_data["is_ephys_session"] = "settings.ephys" in session_data

    return session_data


if __name__ == "__main__":
    import murineshiftwork
    from murineshiftwork.logic.log import setup_logging

    setup_logging()

    BASE_PATH = Path(murineshiftwork.__path__[0]).parent / "tests"

    # Incomplete session
    TEST_FILE_1 = (
        BASE_PATH
        / "_test_subject/_test_subject__20211004_191858__probabilistic_switching"
    )

    # Legacy format
    TEST_FILE_2 = (
        BASE_PATH
        / "sleep_lhb_c344986_m1097354__20210718_152153__probabilistic_switching"
    )

    # Current format
    TEST_FILE_3 = (
        BASE_PATH
        / "tab_npx_007_m1114799_LL_chrOn__20210928_120653__probabilistic_switching"
    )

    session_data = read_session_data(session_dir=TEST_FILE_1, load_raw=False)

    print(" ")
