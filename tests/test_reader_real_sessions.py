"""Reader tests against real session data in /mnt/maindata/data.

All tests are skipped when the data dir is not available (CI-safe).
"""
import pytest
from pathlib import Path

DATA_DIR = Path("/mnt/maindata/data")
pytestmark = pytest.mark.skipif(
    not DATA_DIR.exists(), reason="Real data dir not available"
)


def _all_session_dirs():
    return sorted(
        d for subj in DATA_DIR.iterdir() if subj.is_dir()
        for d in subj.iterdir() if d.is_dir()
    )


def _session_dirs_with_jsonl():
    return [d for d in _all_session_dirs() if list(d.glob("*.df.jsonl"))]


@pytest.fixture(scope="module")
def first_session_dir():
    dirs = _session_dirs_with_jsonl()
    if not dirs:
        pytest.skip("No JSONL sessions found")
    return dirs[0]


@pytest.fixture(scope="module")
def all_session_dirs_with_data():
    return _session_dirs_with_jsonl()


# ---------------------------------------------------------------------------
# load_trial_data (raw list)

def test_load_trial_data_returns_list(first_session_dir):
    from murineshiftwork.logic.io import load_trial_data
    jsonl = list(first_session_dir.glob("*.df.jsonl"))[0]
    trials = load_trial_data(jsonl)
    assert isinstance(trials, list)


def test_load_trial_data_skips_version_header(first_session_dir):
    from murineshiftwork.logic.io import load_trial_data
    jsonl = list(first_session_dir.glob("*.df.jsonl"))[0]
    trials = load_trial_data(jsonl)
    # No trial dict should have the version header key
    assert all("_msw_version" not in t for t in trials)


def test_load_trial_data_nonempty_session(all_session_dirs_with_data):
    from murineshiftwork.logic.io import load_trial_data
    # Find a session with trials (not just header + 0 trials)
    found = False
    for sdir in all_session_dirs_with_data:
        jsonl = list(sdir.glob("*.df.jsonl"))[0]
        trials = load_trial_data(jsonl)
        if len(trials) > 0:
            found = True
            assert isinstance(trials[0], dict)
            break
    assert found, "Could not find any session with trial data"


# ---------------------------------------------------------------------------
# read_session_data (full reader)

def test_read_session_data_keys(first_session_dir):
    from murineshiftwork.readers.session import read_session_data
    d = read_session_data(str(first_session_dir))
    assert "msw_version" in d
    assert "is_legacy_session" in d
    assert "is_complete_session" in d


def test_read_session_data_not_legacy(first_session_dir):
    from murineshiftwork.readers.session import read_session_data
    d = read_session_data(str(first_session_dir))
    assert d["is_legacy_session"] is False
    assert d["msw_version"] == "1.0.0"


def test_read_session_data_complete(first_session_dir):
    from murineshiftwork.readers.session import read_session_data
    d = read_session_data(str(first_session_dir))
    assert d["is_complete_session"] is True


def test_read_session_data_df_is_dataframe_or_none(first_session_dir):
    import pandas as pd
    from murineshiftwork.readers.session import read_session_data
    d = read_session_data(str(first_session_dir))
    assert d.get("df") is None or isinstance(d["df"], pd.DataFrame)


def test_read_session_data_with_real_trials():
    from murineshiftwork.readers.session import read_session_data
    import pandas as pd

    for sdir in _session_dirs_with_jsonl():
        from murineshiftwork.logic.io import load_trial_data
        jsonl = list(sdir.glob("*.df.jsonl"))[0]
        if len(load_trial_data(jsonl)) > 5:
            d = read_session_data(str(sdir))
            df = d.get("df")
            assert df is not None
            assert isinstance(df, pd.DataFrame)
            assert df.shape[0] > 0
            # Standard columns from pybpod
            assert "Bpod start timestamp" in df.columns or "Trial start timestamp" in df.columns
            return

    pytest.skip("No session with >5 trials found")


def test_read_multiple_subjects():
    from murineshiftwork.readers.session import read_session_data
    subjects = [d for d in DATA_DIR.iterdir() if d.is_dir()]
    assert len(subjects) >= 1
    read_ok = 0
    for subj in subjects[:3]:
        for sdir in sorted(subj.iterdir()):
            if not sdir.is_dir():
                continue
            if not list(sdir.glob("*.df.jsonl")):
                continue
            d = read_session_data(str(sdir))
            assert "msw_version" in d
            read_ok += 1
            break
    assert read_ok >= 1
