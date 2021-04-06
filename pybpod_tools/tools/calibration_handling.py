import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from pybpod_tools.config_files import calibration_data_folder

calibration_file_sound_delay = calibration_data_folder / "sound_delay.csv"
calibration_file_sound_delay_fig = calibration_data_folder / "sound_delay.png"
calibration_file_water_calibration = calibration_data_folder / "water_calibration.csv"


def load_sound_delay_data():
    if Path(calibration_file_sound_delay).exists():
        return pd.read_csv(calibration_file_sound_delay)
    else:
        return pd.DataFrame()


def save_sound_delay_data(measurements=None, plot=True, overwrite=True):
    delay_measurements_df = pd.DataFrame(measurements)
    delays = delay_measurements_df["delay"] * 1000  # convert to msec

    if Path(calibration_file_sound_delay).exists() and not overwrite:
        raise FileExistsError(
            f"Not allowed to overwrite existing calibration file: {calibration_file_sound_delay}"
        )
    else:
        delay_measurements_df.to_csv(calibration_file_sound_delay)

    if plot:
        save_sound_delay_figure(delay_data=delays)

    logging.info(
        f"Delay sound trigger to soundcard TTL is\n"
        f"\tMEAN={np.round(delays.mean(), 3)}ms\n"
        f"\tMEDIAN={np.round(delays.median(), 3)}ms\n"
        f"\tSTD={np.round(delays.std(), 3)}ms\n"
    )


def save_sound_delay_figure(delay_data=None):
    f = plt.figure(dpi=450)
    plt.plot(delay_data, "k*--")
    plt.title("Delays sound softcode to soundcard TTL received by Bpod.")
    plt.ylabel("Delay [ms]")
    plt.xlabel("Trial [#]")
    f.savefig(calibration_file_sound_delay_fig)


def load_water_calibration():
    if Path(calibration_file_water_calibration).exists():
        return pd.read_csv(calibration_file_water_calibration)
    else:
        return pd.DataFrame()


def convert_gram_to_microliter(weight_g=None, n_drops=None):
    return weight_g / n_drops * 1000  # covert to microliter


def save_water_calibration(df=None, overwrite=True):
    if Path(calibration_file_water_calibration).exists() and not overwrite:
        raise FileExistsError(
            f"Not allowed to overwrite existing calibration file: {calibration_file_water_calibration}"
        )
    else:
        df.to_csv(calibration_file_water_calibration)


def _exponential_function(x, a, b, c):
    return a * np.exp(-b * x) + c


def fit_water_calibration_exp(x_observed=None, y_observed=None):
    # x = np.linspace(0, 4, 50)
    # y = _exponential_function(x, 2.5, 1.3, 0.5)
    # yn = y + 0.2 * np.random.normal(size=len(x))

    popt, pcov = curve_fit(_exponential_function, x_observed, y_observed)
    return popt, pcov


def evaluate_water_calibration_curve_continuous(popt=None, min=0, max=10, step=0.1):
    x_continuous = np.linspace(min, max, int(max / step), endpoint=True)
    y_continuous = _exponential_function(x_continuous, *popt)
    return x_continuous, y_continuous


def evaluate_water_calibration_curve_y_to_x(x_continuous, y_continuous, y_target=None):
    x_value = np.interp(y_target, x_continuous, y_continuous)
    return x_value
