import re
import socket
from datetime import datetime
from pathlib import Path

MSW_DATETIME_FORMAT = "%Y%m%d_%H%M%S_%f"

# Characters that are forbidden in subject/task path components.
# Includes shell special chars, glob chars, and common typos (#, @, !, space).
_FORBIDDEN_PATH_CHARS = re.compile(r'[#@!$%^&*()+=\[\]{};:\'",<>?\\|`~ ]')


def test_path_is_writable(path=None):
    try:
        with open(path, "w"):
            pass
        if Path(path).exists():
            Path(path).unlink()
    except PermissionError:
        return False
    return True


def build_data_paths(
    basepath=None,
    subject=None,
    task=None,
    default_subject="_test_subject",
    is_child_session_to=None,
    printout=True,
):
    basepath = Path(basepath)

    # Session & file names
    subject = default_subject if str(task).startswith("_test__") else subject
    if subject and _FORBIDDEN_PATH_CHARS.search(subject):
        bad = _FORBIDDEN_PATH_CHARS.findall(subject)
        raise ValueError(
            f"Subject name contains forbidden characters {bad!r}: {subject!r}. "
            f"Use only letters, digits, hyphens, and underscores."
        )
    dt = datetime.now().strftime(MSW_DATETIME_FORMAT)
    session_basename = "__".join([subject, dt, task])

    # Folder hierarchy
    session_data_folder = (
        basepath / subject / is_child_session_to / session_basename
        if is_child_session_to is not None
        else basepath / subject / session_basename
    )

    session_behaviour_basename = session_data_folder / session_basename

    session_paths = {
        "subject": subject,
        "datetime": dt,
        "task": task,
        "basepath": basepath,
        # Main vars for usage
        "session_basename": session_basename,
        "session_basename_behav": session_basename + ".msw",
        "session_folder": str(session_data_folder),
        "session_file_path": str(session_behaviour_basename),
    }

    if printout:
        print("\n   Session paths: \n")
        for k, v in session_paths.items():
            print(f"{k:>30}:{'':>2}{v}")
        print("\n")

    return session_paths


def get_host_ip():
    """Source: https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP


def get_host_name():
    return socket.gethostname()
