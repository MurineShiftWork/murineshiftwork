from datetime import datetime
from pathlib import Path


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
    skip_subject_folder=False,
    printout=True,
):
    basepath = Path(basepath)

    # Session & file names
    subject = default_subject if str(task).startswith("_test__") else subject
    dt = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_basename = "__".join([subject, dt, task])

    # Folder hierarchy
    if skip_subject_folder:
        session_data_folder = basepath / session_basename
    else:
        session_data_folder = basepath / subject / session_basename

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
