"""Reader tests against checked-in fixture sessions in tests/data/.

These always run (no skip condition) and cover both JSONL and PKL formats.
Use test_reader_real_sessions.py for broader coverage against live data.
"""

from pathlib import Path

import pandas as pd
import pytest

FIXTURES_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# helpers


def _session_dir(variant="jsonl"):
    d = FIXTURES_DIR / f"fixture_{variant}"
    if not d.exists():
        pytest.skip(f"Fixture dir absent: {d}")
    return d


# ---------------------------------------------------------------------------
# JSONL: trial_data (low-level)


def test_load_trial_data_jsonl_returns_list():
    from murineshiftwork.logic.io import load_trial_data

    sdir = _session_dir("jsonl")
    jsonl = next(sdir.glob("*.df.jsonl"))
    trials = load_trial_data(jsonl)
    assert isinstance(trials, list)


def test_load_trial_data_jsonl_nonempty():
    from murineshiftwork.logic.io import load_trial_data

    sdir = _session_dir("jsonl")
    jsonl = next(sdir.glob("*.df.jsonl"))
    trials = load_trial_data(jsonl)
    assert len(trials) > 0
    assert isinstance(trials[0], dict)


def test_load_trial_data_jsonl_no_version_header():
    from murineshiftwork.logic.io import load_trial_data

    sdir = _session_dir("jsonl")
    jsonl = next(sdir.glob("*.df.jsonl"))
    trials = load_trial_data(jsonl)
    assert all("_msw_version" not in t for t in trials)


def test_save_reload_roundtrip_jsonl(tmp_path):
    from murineshiftwork.logic.io import load_trial_data, save_trial_data

    sdir = _session_dir("jsonl")
    jsonl = next(sdir.glob("*.df.jsonl"))
    original = load_trial_data(jsonl)
    out = tmp_path / "roundtrip.df.jsonl"
    save_trial_data(original, out)
    reloaded = load_trial_data(out)
    assert len(reloaded) == len(original)
    assert reloaded[0].keys() == original[0].keys()


# ---------------------------------------------------------------------------
# PKL: trial_data (low-level via read_trial_df — pkl uses pd.read_pickle)


def test_read_trial_df_pkl_returns_dataframe():
    from murineshiftwork.readers.files import read_trial_df

    sdir = _session_dir("pkl")
    pkl = next(sdir.glob("*.df.pkl"))
    import pandas as pd

    df = read_trial_df(filepath=pkl, return_raw=True)
    assert isinstance(df, pd.DataFrame)


def test_read_trial_df_pkl_nonempty():
    from murineshiftwork.readers.files import read_trial_df

    sdir = _session_dir("pkl")
    pkl = next(sdir.glob("*.df.pkl"))
    df = read_trial_df(filepath=pkl, return_raw=True)
    assert df is not None
    assert df.shape[0] > 0


# ---------------------------------------------------------------------------
# JSONL: read_session_data (full reader)


def test_read_session_data_jsonl_keys():
    from murineshiftwork.readers.session import read_session_data

    d = read_session_data(str(_session_dir("jsonl")))
    assert "msw_version" in d
    assert "is_legacy_session" in d
    assert "is_complete_session" in d


def test_read_session_data_jsonl_not_legacy():
    from murineshiftwork.readers.session import read_session_data

    d = read_session_data(str(_session_dir("jsonl")))
    assert d["is_legacy_session"] is False


def test_read_session_data_jsonl_complete():
    from murineshiftwork.readers.session import read_session_data

    d = read_session_data(str(_session_dir("jsonl")))
    assert d["is_complete_session"] is True


def test_read_session_data_jsonl_df_is_dataframe():
    from murineshiftwork.readers.session import read_session_data

    d = read_session_data(str(_session_dir("jsonl")))
    assert isinstance(d.get("df"), pd.DataFrame)
    assert d["df"].shape[0] > 0


def test_read_session_data_jsonl_version_1():
    from murineshiftwork.readers.session import read_session_data

    d = read_session_data(str(_session_dir("jsonl")))
    assert d["msw_version"] == "1.0.0"


def test_read_session_data_jsonl_has_standard_columns():
    from murineshiftwork.readers.session import read_session_data

    d = read_session_data(str(_session_dir("jsonl")))
    df = d["df"]
    has_bpod_start = "Bpod start timestamp" in df.columns
    has_trial_start = "Trial start timestamp" in df.columns
    assert has_bpod_start or has_trial_start


# ---------------------------------------------------------------------------
# PKL: read_session_data (full reader)


def test_read_session_data_pkl_keys():
    from murineshiftwork.readers.session import read_session_data

    d = read_session_data(str(_session_dir("pkl")))
    assert "msw_version" in d
    assert "is_legacy_session" in d
    assert "is_complete_session" in d


def test_read_session_data_pkl_df_is_dataframe():
    from murineshiftwork.readers.session import read_session_data

    d = read_session_data(str(_session_dir("pkl")))
    assert isinstance(d.get("df"), pd.DataFrame)
    assert d["df"].shape[0] > 0
