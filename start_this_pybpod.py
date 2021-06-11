def main():
    from murine_shift_work.tools.run_install_tasks import run_check_install

    run_check_install()

    from pybpodgui_plugin.__main__ import start

    start()


if __name__ == "__main__":
    main()
