import sys

from murineshiftwork.cli import run_cli

a = """run
-t
fixedsubj
-b
/dev/ttyACM2
-stage
/dev/ttyUSB0
-cs
/mnt/maindata/CONFIG_FILES/subject.settings
-cc
/mnt/maindata/CONFIG_FILES/camera.rcc.setup2.fixed.from.murinemanager
-cwater
~/.murineshiftwork/calibration.water.setup2.csv
-cstage
~/.murineshiftwork/calibration.stage.setup2.yaml
-meta
x=11
y=12
z=13
"""

b = """run
-t
fixedsubject
-b
/dev/ttyACM1
-stage
/dev/ttyUSB2
-cs
/mnt/maindata/CONFIG_FILES/subject.settings
-cc
/mnt/maindata/CONFIG_FILES/camera.rcc.setup3.fixed.from.murinemanager
-cwater
~/.murineshiftwork/calibration.water.setup3.csv
-cstage
~/.murineshiftwork/calibration.stage.setup3.yaml
-meta
x=41
y=42
z=43
"""

if __name__ == "__main__":
    argsplit = b.split("\n")
    print(argsplit)
    args = sys.argv + argsplit
    # + ['bla_var="split word"', "some_other_var=243"]  # .split(" ")
    run_cli(*args)
