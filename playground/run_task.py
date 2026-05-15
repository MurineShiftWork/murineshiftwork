import sys

from murineshiftwork.cli import run_cli


if __name__ == "__main__":
    args = (
        sys.argv + "run "
        "-t fixedsubjects "
        "-b /dev/ttyACM0 "
        "-stage /dev/ttyUSB0 "
        "-cs /mnt/maindata/CONFIG_FILES/subject.settings "
        "-cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup1.fixed.from.murinemanager "
        "-cwater ~/.murineshiftwork/calibration.water.setup1.csv "
        "-cstage ~/.murineshiftwork/calibration.stage.setup1.yaml "
        "-o /mnt/maindata/data "
        "-meta x=11 y=12 z=13 "
        "-s _test_subject "
        "-d".split(" ")  # + ['bla_var="split word"', "some_other_var=243"]
    )  # .split(" ")
    run_cli(*args)

#  murineshiftwork run
#  -t fixedsubj
#  -b /dev/ttyACM0
#  -stage /dev/ttyUSB0
#  -cs /mnt/maindata/CONFIG_FILES/subject.settings
#  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup1.fixed.from.murinemanager
#  -cwater ~/.murineshiftwork/calibration.water.setup1.csv
#  -cstage ~/.murineshiftwork/calibration.stage.setup1.yaml
#  -meta x=11 y=12 z=13
#  -o /mnt/maindata/data/
