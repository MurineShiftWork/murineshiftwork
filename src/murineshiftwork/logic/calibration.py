import logging
import os.path
import shutil
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.optimize import curve_fit


class CalibrationData:
    file_path = None
    calibration_data = None
    columns = []
    columns_to_drop = ["Unnamed: 0"]

    def __init__(self, file_path=None, **kwargs):
        """ """
        super(CalibrationData, self).__init__(**kwargs)
        self.file_path = file_path or self.file_path
        print(f"CALIBRATION DATA PATH: {self.file_path}")

        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

        self.load()

    def __add__(self, other):
        assert isinstance(other, dict)
        other.update({"measurement_time": datetime.now()})
        self.calibration_data = self.calibration_data._append(
            other, ignore_index=True
        )
        return self

    def __repr__(self):
        return f"{type(self)} with {self.calibration_data.shape[0]} entries."

    def __str__(self):
        return str(self.calibration_data)

    def make_output_dir(self):
        if self.file_path is None:
            return
        if not self.file_path.parent.exists():
            self.file_path.parent.mkdir(exist_ok=True, parents=True)

    def load(self, file_path=None):
        if file_path is not None:
            self.file_path = file_path

        if Path(self.file_path).exists():
            self.calibration_data = pd.read_csv(self.file_path)
            logging.debug(
                f"Updated calibration data with {self.calibration_data.shape[0]} measurements."
            )
        else:
            self.calibration_data = pd.DataFrame(columns=self.columns)

        for target_column in self.columns_to_drop:
            if target_column in self.calibration_data.columns:
                self.calibration_data = self.calibration_data.drop(
                    target_column, axis=1
                )

        return self.calibration_data

    def save(self, file_path=None, overwrite=False):
        if file_path is not None:
            self.file_path = file_path

        file_path = Path(self.file_path)
        if (
            self.calibration_data is not None
            and not self.calibration_data.empty
        ):
            file_path.expanduser().parent.mkdir(exist_ok=True, parents=True)

            if file_path.exists() and not overwrite:
                raise FileExistsError(
                    f"File exists and not allowed to overwrite. {file_path}"
                )
            self.calibration_data.to_csv(file_path)
            print(f"SAVING calibration at: {file_path}")


class CalibrationDataWater(CalibrationData):
    allowable_offset_days = 30
    columns = [
        "measurement_time",
        "valve_id",
        "valve_opening_time",
        "n_drops",
        "inter_pulse_interval",
        "weight",
        "weight_per_drop",
        "volume_ul",
    ]

    def add_calibration_point(
        self,
        valve_id=None,
        valve_opening_time=None,
        n_drops=None,
        inter_pulse_interval=None,
        water_weight_g=None,
    ):
        self.__add__(
            {
                "valve_id": valve_id,
                "valve_opening_time": valve_opening_time,
                "n_drops": n_drops,
                "inter_pulse_interval": inter_pulse_interval,
                "water_weight_g": water_weight_g,
            }
        )

    def water_volume_to_valve_time(
        self, valves=None, target_volume=None, s_to_ms=1000
    ):
        if (
            self.calibration_data is not None
            and not self.calibration_data.empty
        ):
            self.upgrade_calibration_file_field_names()

            # Process calibration data
            self.calibration_data["weight_per_drop"] = np.round(
                self.calibration_data["water_weight_g"]
                / self.calibration_data["n_drops"],
                3,
            )
            self.calibration_data["volume_ul"] = np.round(
                self.calibration_data["weight_per_drop"] * 1e3, 3
            )
            self.calibration_data = self.calibration_data.sort_values(
                by="valve_opening_time"
            )

            if not hasattr(valves, "__iter__"):
                valves = [valves]

            print(self.calibration_data)
            # Get target valve opening times for given volumes
            calibration_targets = {}
            for this_valve in valves:
                data_for_valve = self.calibration_data.loc[
                    self.calibration_data["valve_id"] == this_valve
                ]

                # FIXME: REPLACE INTERP WITH CURVE FIT. SEE FUNCTIONS BELOW

                calibration_targets[this_valve] = (
                    np.interp(
                        target_volume,
                        data_for_valve["volume_ul"],
                        data_for_valve["valve_opening_time"],
                    )
                    / s_to_ms
                )
            return calibration_targets

    def save_calibration_plot(self):
        if (
            self.file_path is not None
            and self.calibration_data is not None
            and not self.calibration_data.empty
        ):
            # TODO: move processing block into separate fct that gets called after calibration, before saving as well!
            # Process calibration data
            self.calibration_data["weight_per_drop"] = np.round(
                self.calibration_data["water_weight_g"]
                / self.calibration_data["n_drops"],
                3,
            )
            self.calibration_data["volume_ul"] = np.round(
                self.calibration_data["weight_per_drop"] * 1e3, 3
            )
            self.calibration_data = self.calibration_data.sort_values(
                by="valve_opening_time"
            )

            # PLOT
            f = plt.figure(dpi=450)
            sns.lineplot(
                data=self.calibration_data,
                x="valve_opening_time",
                y="volume_ul",
                hue="valve_id",
            )
            plt.title("Valve opening times to pass water volume [uL].")
            plt.ylabel("Volume [uL]")
            plt.xlabel("Valve opening time [ms]")
            f.savefig(os.path.splitext(self.file_path)[0] + ".png")

    def upgrade_calibration_file_field_names(self):
        """Ensure compatibility between old calibration data files and new columns format."""
        if "microliters" in self.calibration_data.columns:
            logging.debug(
                "Water calibration file has old field names. Making backup copy and overwriting original.."
            )
            self.calibration_data = self.calibration_data.rename(
                {
                    "valve": "valve_id",
                    "valve_time": "valve_opening_time",
                    "weight": "water_weight_g",
                    "microliters": "volume_ul",
                }
            )
            backup_file = str(self.file_path) + ".bak"
            shutil.copyfile(src=self.file_path, dst=backup_file)
            if Path(backup_file).exists():
                self.save()
            else:
                raise FileNotFoundError(
                    f"backup file should have been made by copying {self.file_path} to {backup_file}."
                )


class CalibrationDataSound(CalibrationData):
    columns = ["measurement_time", "trial", "delay"]

    def add_calibration_point(self, trial=None, delay=None):
        self.__add__(
            {
                "trial": trial,
                "delay": delay,
            }
        )

    def calculate_sound_delay_correction(self):
        return np.round(self.calibration_data["delay"].median(), 3)

    def save_calibration_plot(self):
        if (
            self.file_path is not None
            and self.calibration_data is not None
            and not self.calibration_data.empty
        ):
            f = plt.figure(dpi=450)
            plt.plot(self.calibration_data["delay"] * 1000, "k*--")
            plt.title(
                "Delays from sound softcode to soundcard TTL received by Bpod BNC-in."
            )
            plt.ylabel("Delay [ms]")
            plt.xlabel("Trial [#]")
            f.savefig(os.path.splitext(self.file_path)[0] + ".png")


def _exponential_function(x, a, b, c):
    return a * np.exp(b * x) + c


def fit_water_calibration_exp(x_observed=None, y_observed=None):
    # x = np.linspace(0, 4, 50)
    # y = _exponential_function(x, 2.5, 1.3, 0.5)
    # yn = y + 0.2 * np.random.normal(size=len(x))

    popt, pcov = curve_fit(_exponential_function, x_observed, y_observed)
    return popt, pcov


def evaluate_water_calibration_curve_continuous(
    popt=None, min=0, max=10, step=0.1
):
    x_continuous = np.linspace(min, max, int(max / step), endpoint=True)
    y_continuous = _exponential_function(x_continuous, *popt)
    return x_continuous, y_continuous


def evaluate_water_calibration_curve_y_to_x(
    x_continuous, y_continuous, y_target=None
):
    x_value = np.interp(y_target, x_continuous, y_continuous)
    return x_value
