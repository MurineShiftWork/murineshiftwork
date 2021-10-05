from glob import glob
from pathlib import Path

from murine_shift_work.readers.files import read_json
from murine_shift_work.readers.files import read_pybpod_csv
from murine_shift_work.readers.files import read_settings_py
from murine_shift_work.readers.files import read_trial_df
from murine_shift_work.readers.namespace import test_is_legacy_format
from murine_shift_work.readers.namespace import test_is_recognized_msw_file


def read_session_data(
    session_dir=None,
    load_raw=False,
    ignore_errors=True,
):
    """Read session data for this acquisition package.

    Namespace:
        - current files all have a "*.msw.*" segment after the session name
        - legacy files differ:
            - task settings:    "task_settings.py"
            - df:               ".msw.pkl" or "switching.pkl"
            - csv:              ".msw.csv" or "switching.csv"

    Expected files:
        - Trial dataframe:      .msw.pkl or .msw.df.pkl
        - Raw pybpod data:      .msw.csv or .csv [might be ambiguous with RCC files]
        - 2 settings files:     .msw.settings.[task|process].json

    :param session_dir:
    :param load_raw:
    :param ignore_errors:
    :return:
    """
    session_dir = Path(session_dir)
    assert session_dir.exists()

    files_in_dir = glob(str(session_dir / "*"))

    session_files_dict = {
        v.split(".msw.")[-1]: v for v in files_in_dir if test_is_recognized_msw_file(v)
    }
    is_legacy_session = test_is_legacy_format(session_dir=session_dir)

    session_data = {}
    for k, v in session_files_dict.items():
        if Path(k).name.endswith("csv"):
            # Add key for session completeness, but might be empty if input load_raw=False
            session_data["raw"] = None
            if load_raw:
                session_data["raw"] = read_pybpod_csv(filepath=v)

        elif Path(k).name.endswith("pkl"):
            session_data["df"] = read_trial_df(filepath=v)

        elif k.endswith("json") and ".msw." in v:
            # 2 files: task & process
            session_data[k.replace(".json", "")] = read_json(file=session_files_dict[k])

        elif Path(k).name == "task_settings.py" and is_legacy_session:
            session_data["settings.task"] = read_settings_py(filepath=v)

        else:
            print(f"Unrecognized file: {k} - {v}")

    # Check if session data is complete
    required_file_keys = ["raw", "df", "settings.task"]
    if not is_legacy_session:
        required_file_keys += ["settings.process"]

    session_data["is_complete_session"] = True
    for k in required_file_keys:
        if k not in session_data:
            session_data["complete_session"] = False

    return session_data


if __name__ == "__main__":
    import murine_shift_work
    from murine_shift_work.logic.log import setup_logging

    setup_logging()

    BASE_PATH = Path(murine_shift_work.__path__[0]).parent / "tests"

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
