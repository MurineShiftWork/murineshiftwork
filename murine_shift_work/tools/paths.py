import os
from datetime import datetime

from confapp import conf as confsett

from murine_shift_work.tools.run_install_tasks import get_default_data_path


def make_session_paths(protocol=None, show=True):
    protocol, _ = os.path.splitext(str(protocol))
    subject = (
        "_test_subject"
        if str(protocol).startswith("_test__")
        else eval(confsett.PYBPOD_SUBJECTS[0])[0]
    )
    dt = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_basename = "__".join([subject, dt, protocol])

    get_default_data_path().mkdir(exist_ok=True, parents=True)

    session_data_folder = get_default_data_path() / subject / session_basename
    session_data_folder.mkdir(exist_ok=True, parents=True)
    session_behaviour_basename = session_data_folder / session_basename

    session_paths = {
        "subject": subject,
        "datetime": dt,
        "protocol": str(protocol),
        "base_data_folder": get_default_data_path(),
        # Main vars for usage
        "session_basename": session_basename,
        "session_data_folder": str(session_data_folder),
        "session_behaviour_basename": str(session_behaviour_basename),
    }

    if show:
        print("\n   Session paths: \n")
        for k, v in session_paths.items():
            print(f"{k:>30}:{'':>2}{v}")
        print("\n")
    return session_paths
