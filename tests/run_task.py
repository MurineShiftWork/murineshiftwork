import sys

from murine_shift_work.cli import run_cli


if __name__ == "__main__":
    args = (
        sys.argv + "run "
        "-t fixedsubjects "
        "-b /dev/ttyACM1 "
        "-cs /home/lbr/CONFIG_FILES/subject.settings "
        "-cc /home/lbr/CONFIG_FILES/camera.rcc.setup5.fixed "
        "-d".split(" ")  # + ['bla_var="split word"', "some_other_var=243"]
    )  # .split(" ")
    run_cli(*args)
