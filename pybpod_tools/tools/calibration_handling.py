import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pybpod_tools.config_files import calibration_data_folder


def load_sound_delay_data():
    return pd.read_csv(calibration_data_folder / "sound_delay.csv")


def save_sound_delay_data(measurements=None, plot=True):
    delay_measurements_df = pd.DataFrame(measurements)
    delays = delay_measurements_df["delay"] * 1000  # convert to msec

    delay_measurements_df.to_csv(calibration_data_folder / "sound_delay.csv")

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
    f.savefig(calibration_data_folder / "sound_delay.png")


def load_water_calibration():
    return pd.read_csv(calibration_data_folder / "water_calibration.csv")


def save_water_calibration(df=None):
    df.to_csv(calibration_data_folder / "water_calibration.csv")
