import logging
from glob import glob
from pathlib import Path


def test_is_legacy_msw_file(file):
    """Test if file is legacy namespace file."""
    file = str(file)
    return (
        Path(file).name.endswith("switching.pkl")
        or Path(file).name.endswith("switching.csv")
        or Path(file).name.endswith("task_settings.py")
    )


def test_is_recognized_msw_file(file):
    """Test if file is current or legacy namespace file."""
    file = str(file)
    # Back-compat: sequence task previously wrote *.df.jsonl without .msw. segment
    if file.endswith(".df.jsonl") and ".msw." not in file:
        return True
    return ".msw." in file or test_is_legacy_msw_file(file=file)


def test_is_legacy_format(session_dir=None):
    """Test if files in session folder are legacy namespace file."""
    session_dir = Path(session_dir)
    assert session_dir.exists()

    session_files = glob(str(session_dir / "*"))

    for f in session_files:
        if test_is_legacy_msw_file(file=f):
            logging.debug(
                f"Is legacy MSW data format (identified on file: '{Path(f).name}'): {str(session_dir)}"
            )
            return True

    return False
