from pybpodgui_plugin.__main__ import start

from murine_shift_work.tools.run_install_tasks import run_check_install

if __name__ == "__main__":
    run_check_install()
    start()
