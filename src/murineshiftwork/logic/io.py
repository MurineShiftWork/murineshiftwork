"""Version-agnostic trial data serialisation (v2.0.0).

Format: newline-delimited JSON (JSONL). First line is a version header.
Numpy arrays are serialised as plain lists; on load they remain lists,
which is compatible with all downstream DataFrame operations.

Tuple preservation
------------------
JSON has no tuple type — both lists and tuples serialise as arrays. To preserve
Python tuples across the round-trip, tuples are encoded as {"__tuple__": [...]}
and decoded back to tuples on load. This keeps the computational interface
identical between JSONL and legacy pkl sessions (e.g. block_type_values).
"""

import json
import logging
from pathlib import Path

import numpy as np

MSW_FILE_VERSION = "1.0.0"


def _encode_tuples(obj):
    """Recursively replace tuples with {"__tuple__": [...]} before JSON encoding."""
    if isinstance(obj, tuple):
        return {"__tuple__": [_encode_tuples(v) for v in obj]}
    if isinstance(obj, dict):
        return {k: _encode_tuples(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_encode_tuples(v) for v in obj]
    return obj


def _decode_tuples(obj):
    """Recursively restore {"__tuple__": [...]} sentinels to Python tuples."""
    if isinstance(obj, dict):
        if "__tuple__" in obj and len(obj) == 1:
            return tuple(_decode_tuples(v) for v in obj["__tuple__"])
        return {k: _decode_tuples(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decode_tuples(v) for v in obj]
    return obj


class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)


def save_trial_data(trial_data_list: list, filepath) -> None:
    """Save list of trial dicts to JSONL (overwrites existing file)."""
    filepath = Path(filepath)
    with filepath.open("w") as f:
        f.write(json.dumps({"_msw_version": MSW_FILE_VERSION}) + "\n")
        for trial in trial_data_list:
            f.write(json.dumps(_encode_tuples(trial), cls=_NumpyEncoder) + "\n")
    logging.debug(f"Saved {len(trial_data_list)} trials to {filepath}")


def load_trial_data(filepath) -> list:
    """Load trial dicts from JSONL file, skipping the version header."""
    filepath = Path(filepath)
    trials = []
    with filepath.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "_msw_version" in obj:
                continue
            trials.append(_decode_tuples(obj))
    return trials
