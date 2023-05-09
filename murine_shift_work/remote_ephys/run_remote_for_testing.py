import sys

from murine_shift_work.remote_ephys import run_remote_ephys

if __name__ == "__main__":
    # import sys
    sys.argv += ["--record"]  #  "--is-child-session-to", "ch-sess"
    run_remote_ephys()

    print("x")
