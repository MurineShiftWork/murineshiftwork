import sys

from murine_shift_work.cli import run_cli


if __name__ == "__main__":
    args = (
        sys.argv + "run "
        "-t fixedsubjects "
        "-cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup1.fixed.from.murinemanager "
        "-b /dev/ttyACM1 "
        "-s _test_subject "
        "-d".split(" ")  # + ['bla_var="split word"', "some_other_var=243"]
    )  # .split(" ")
    run_cli(*args)
