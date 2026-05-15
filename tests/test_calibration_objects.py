from murineshiftwork.logic.calibration import CalibrationDataSound
from murineshiftwork.logic.calibration import CalibrationDataWater

cs = CalibrationDataSound(
    file_path="../murineshiftwork/settings/calibration.sound.default.csv"
)
cw = CalibrationDataWater(
    file_path="../murineshiftwork/settings/calibration.water.default.csv"
)


cw.water_volume_to_valve_time(valves=1, target_volume=5)
print(" ")

# c.add_calibration_point(trial=5, delay=55)
#
# c += {"trial": 5, "delay": 30}

print(" ")
