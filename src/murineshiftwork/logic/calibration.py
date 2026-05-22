import logging
import os.path
import shutil
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.optimize import OptimizeWarning, curve_fit


class CalibrationData:
    file_path = None
    calibration_data: Any = None
    columns: list = []
    columns_to_drop = ["Unnamed: 0"]

    def __init__(self, file_path=None, **kwargs):
        """ """
        super(CalibrationData, self).__init__(**kwargs)
        self.file_path = file_path or self.file_path
        logging.debug(f"Calibration data path: {self.file_path}")

        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

        self.load()

    def __add__(self, other):
        assert isinstance(other, dict)
        other.update({"measurement_time": datetime.now()})
        import pandas as pd

        self.calibration_data = pd.concat(
            [self.calibration_data, pd.DataFrame([other])], ignore_index=True
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

        if self.file_path and Path(self.file_path).exists():
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
        if self.calibration_data is not None and not self.calibration_data.empty:
            file_path.expanduser().parent.mkdir(exist_ok=True, parents=True)

            if file_path.exists() and not overwrite:
                raise FileExistsError(
                    f"File exists and not allowed to overwrite. {file_path}"
                )
            self.calibration_data.to_csv(file_path)
            logging.info(f"Saved calibration: {file_path}")


class CalibrationDataLiquid(CalibrationData):
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

    def load(self, file_path=None):
        if file_path is not None:
            self.file_path = file_path
        # Back-compat: if the .liquid. file doesn't exist, try the old .water. name
        if self.file_path and not Path(self.file_path).exists():
            old_path = str(self.file_path).replace(".liquid.", ".water.")
            if old_path != str(self.file_path) and Path(old_path).exists():
                logging.warning(
                    f"Calibration file not found at {self.file_path}; "
                    f"falling back to legacy path {old_path}. "
                    f"Rename it to {Path(self.file_path).name} to silence this warning."
                )
                self.file_path = old_path
        return super().load()

    def add_calibration_point(
        self,
        valve_id=None,
        valve_opening_time=None,
        n_drops=None,
        inter_pulse_interval=None,
        liquid_weight_g=None,
    ):
        self.__add__(
            {
                "valve_id": valve_id,
                "valve_opening_time": valve_opening_time,
                "n_drops": n_drops,
                "inter_pulse_interval": inter_pulse_interval,
                "liquid_weight_g": liquid_weight_g,
            }
        )

    def _compute_volumes(self):
        """Compute weight_per_drop and volume_ul columns in-place. Idempotent."""
        self.upgrade_calibration_file_field_names()
        self.calibration_data["weight_per_drop"] = np.round(
            self.calibration_data["liquid_weight_g"] / self.calibration_data["n_drops"],
            3,
        )
        self.calibration_data["volume_ul"] = np.round(
            self.calibration_data["weight_per_drop"] * 1e3, 3
        )
        self.calibration_data = self.calibration_data.sort_values(
            by="valve_opening_time"
        )

    def liquid_volume_to_valve_time(self, valves=None, target_volume=None):
        if self.calibration_data is None or self.calibration_data.empty:
            raise ValueError(
                f"Liquid calibration data is empty. "
                f"Ensure a calibration CSV exists at: {self.file_path}"
            )
        self._compute_volumes()

        if not hasattr(valves, "__iter__"):
            valves = [valves]

        # Get target valve opening times (seconds) for given volumes via exponential fit.
        # Preferred path: use SetupConfig.valve_s_for_ul() which calls
        # ValveCalibration.s_for_ul() with the same exponential model.
        # This CSV path is kept for backward compat when SetupConfig is absent.
        calibration_targets = {}
        for this_valve in valves:
            data_for_valve = self.calibration_data.loc[
                self.calibration_data["valve_id"] == this_valve
            ].sort_values("valve_opening_time")

            points = list(
                zip(
                    data_for_valve["valve_opening_time"].tolist(),
                    data_for_valve["volume_ul"].tolist(),
                )
            )
            from murineshiftwork.logic.config import ValveCalibration

            vc = ValveCalibration(points=[[t, u] for t, u in points])
            calibration_targets[this_valve] = vc.s_for_ul(target_volume)
        return calibration_targets

    def save_calibration_plot(self):
        if (
            self.file_path is not None
            and self.calibration_data is not None
            and not self.calibration_data.empty
        ):
            self._compute_volumes()

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

    def to_valve_calibration(self, valve_id: int):
        """Convert collected measurements for one valve into a ValveCalibration.

        Returns a ValveCalibration with the updated timestamp set to now and
        points = [[open_time_ms, volume_ul], ...], one entry per calibration
        measurement, sorted by open time.

        Caller should run .validate() before writing to setup config.
        """
        from datetime import datetime

        from murineshiftwork.logic.config import ValveCalibration

        df = self.calibration_data.copy()
        df = df[df["valve_id"] == valve_id].copy()
        if df.empty:
            raise ValueError(f"No calibration data for valve {valve_id}")

        df["_ul"] = np.round((df["liquid_weight_g"] / df["n_drops"]) * 1e3, 3)
        # Average repeated measurements at the same opening time before converting
        # to points — duplicate times arise when adaptive rounds revisit a time slot.
        df = (
            df.groupby("valve_opening_time", as_index=False)["_ul"]
            .mean()
            .sort_values("valve_opening_time")
        )
        df["_ul"] = np.round(df["_ul"], 3)
        # Drop dead-zone measurements (valve barely opens, volume ≤ 0 is pure noise).
        df = df[df["_ul"] > 0]

        points = [
            [float(row["valve_opening_time"]), float(row["_ul"])]
            for _, row in df.iterrows()
        ]

        return ValveCalibration(
            updated=datetime.now().isoformat(timespec="seconds"),
            points=points,
        )

    def upgrade_calibration_file_field_names(self):
        """Ensure compatibility between old calibration data files and new columns format."""
        if "water_weight_g" in self.calibration_data.columns:
            self.calibration_data = self.calibration_data.rename(
                columns={"water_weight_g": "liquid_weight_g"}
            )
        if "microliters" in self.calibration_data.columns:
            logging.debug(
                "Liquid calibration file has old field names. Making backup copy and overwriting original.."
            )
            self.calibration_data = self.calibration_data.rename(
                {
                    "valve": "valve_id",
                    "valve_time": "valve_opening_time",
                    "weight": "liquid_weight_g",
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


def fit_calibration_exp(x_observed=None, y_observed=None):
    # x = np.linspace(0, 4, 50)
    # y = _exponential_function(x, 2.5, 1.3, 0.5)
    # yn = y + 0.2 * np.random.normal(size=len(x))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OptimizeWarning)
        popt, pcov = curve_fit(_exponential_function, x_observed, y_observed)
    return popt, pcov


def evaluate_calibration_curve_continuous(popt=None, min=0, max=10, step=0.1):
    x_continuous = np.linspace(min, max, int(max / step), endpoint=True)
    y_continuous = _exponential_function(x_continuous, *popt)
    return x_continuous, y_continuous


def evaluate_calibration_curve_y_to_x(x_continuous, y_continuous, y_target=None):
    x_value = np.interp(y_target, x_continuous, y_continuous)
    return x_value


def flag_outlier_points(
    times_s,
    ul_values,
    sigma_threshold: float = 2.0,
):
    """Flag calibration points that deviate significantly from the fitted curve.

    Uses a leave-one-out (LOO) strategy: for each point, the curve is re-fitted
    on all *other* points and the residual of the left-out point is evaluated
    against that fit.  This avoids the masking problem where a single outlier
    pulls the global fit toward itself and hides its own residual.

    The spread of LOO residuals is summarised with the median absolute deviation
    (MAD), which is robust to the presence of one or two outliers.

    Parameters
    ----------
    times_s : array-like
        Valve opening times in seconds.
    ul_values : array-like
        Corresponding volume measurements in µL/drop.
    sigma_threshold : float
        Number of MAD-derived standard-deviation equivalents above which a
        point is flagged as an outlier.

    Returns
    -------
    outlier_mask : np.ndarray of bool
        True for each point that is an outlier.
    residuals : np.ndarray of float
        Signed LOO residuals (observed − predicted) for each point.
    """
    times_s = np.asarray(times_s, dtype=float)
    ul_values = np.asarray(ul_values, dtype=float)

    n = len(times_s)
    if n < 3:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=float)

    # Leave-one-out residuals: fit n-1 points, predict the held-out point
    loo_residuals = np.zeros(n)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        x_loo = times_s[mask]
        y_loo = ul_values[mask]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", OptimizeWarning)
                popt, _ = curve_fit(
                    _exponential_function,
                    x_loo,
                    y_loo,
                    p0=[0.01, 20.0, 0.0],
                    maxfev=5000,
                )
            predicted_i = _exponential_function(times_s[i], *popt)
        except Exception:
            coeffs = np.polyfit(x_loo, y_loo, 1)
            predicted_i = np.polyval(coeffs, times_s[i])
        loo_residuals[i] = ul_values[i] - predicted_i

    # Robust scale: MAD converted to sigma equivalent (Gaussian normalisation)
    # Floor of 1e-6 prevents division by near-zero for perfectly fitted data
    mad = np.median(np.abs(loo_residuals - np.median(loo_residuals)))
    sigma = max(mad * 1.4826, 1e-6)

    outlier_mask = np.abs(loo_residuals) > sigma_threshold * sigma
    return outlier_mask, loo_residuals


# ---------------------------------------------------------------------------
# Calibration visualisation


def plot_setup_valve_calibrations(
    config_dir: str | Path | None = None,
    setup_name: str | None = None,
    save_fig: bool = False,
    show: bool = True,
) -> "plt.Figure":
    """Plot bpod_valve calibration curves for one or all setups.

    Parameters
    ----------
    config_dir:
        Path to the msw_configs directory.  Resolved via machine config if None.
    setup_name:
        If given, plot only that setup.  If None, plot all setups found in
        ``config_dir/setups/``.
    save_fig:
        Save PNG next to each setup YAML when True.
    show:
        Call ``plt.show()`` when True (disable for batch/headless use).

    Returns
    -------
    matplotlib Figure
    """
    import yaml

    from murineshiftwork.logic.machine_config import resolve_config_dir

    config_dir = Path(config_dir) if config_dir else Path(resolve_config_dir())
    setups_dir = config_dir / "setups"

    if setup_name:
        yaml_files = [setups_dir / f"{setup_name}.yaml"]
    else:
        yaml_files = sorted(setups_dir.glob("*.yaml"))

    if not yaml_files:
        raise FileNotFoundError(f"No setup YAMLs found in {setups_dir}")

    # Collect calibration data
    all_data: dict = {}  # {setup_name: {valve_id: {"open_s": [...], "volume_ul": [...]}}}
    for yf in yaml_files:
        if not yf.exists():
            logging.warning(f"Setup YAML not found: {yf}")
            continue
        with open(yf) as f:
            raw = yaml.safe_load(f) or {}
        cal = raw.get("calibrations", {}).get("bpod_valve", {})
        if not cal:
            continue
        sname = raw.get("name", yf.stem)
        all_data[sname] = {}
        for valve_id, vdata in cal.items():
            pts = vdata.get("points", [])
            if not pts:
                continue
            pts_arr = np.array(pts, dtype=float)
            all_data[sname][str(valve_id)] = {
                "open_s": pts_arr[:, 0],
                "volume_ul": pts_arr[:, 1],
                "updated": vdata.get("updated", ""),
            }

    if not all_data:
        raise ValueError("No bpod_valve calibration data found in selected setups.")

    n_setups = len(all_data)
    fig, axes = plt.subplots(
        1, n_setups, figsize=(4 * n_setups, 4), squeeze=False, sharey=False
    )
    fig.suptitle("Bpod valve calibration", fontsize=12)

    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    for col_idx, (sname, valves) in enumerate(all_data.items()):
        ax = axes[0, col_idx]
        for v_idx, (valve_id, vdata) in enumerate(valves.items()):
            x = vdata["open_s"]
            y = vdata["volume_ul"]
            color = colors[v_idx % len(colors)]
            ax.scatter(x, y, color=color, zorder=3, label=f"valve {valve_id}")

            # Fit curve if enough points
            if len(x) >= 3:
                try:
                    mask = y > 0
                    xs, ys = x[mask], y[mask]
                    s_span = float(xs.max() - xs.min()) if len(xs) >= 2 else 1.0
                    ul_min, ul_max = float(ys.min()), float(ys.max())
                    b0 = (
                        np.log(ul_max / ul_min) / s_span
                        if s_span > 0 and ul_min > 0
                        else 5.0
                    )
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", OptimizeWarning)
                        popt, _ = curve_fit(
                            _exponential_function,
                            xs,
                            ys,
                            p0=[ul_min, b0, 0.0],
                            bounds=([0.0, 0.0, -np.inf], [np.inf, np.inf, np.inf]),
                            maxfev=5000,
                        )
                    x_fit = np.linspace(x.min() * 0.9, x.max() * 1.1, 200)
                    y_fit = _exponential_function(x_fit, *popt)
                    ax.plot(x_fit, y_fit, color=color, linewidth=1.2, alpha=0.7)
                except Exception:
                    pass

        ax.set_title(sname, fontsize=10)
        ax.set_xlabel("Valve open time (s)")
        ax.set_ylabel("Volume (µL)")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.tight_layout()

    if save_fig:
        for sname in all_data:
            out = setups_dir / f"{sname}.calibration_plot.png"
            fig.savefig(out, dpi=150)
            logging.info(f"Saved calibration plot: {out}")

    if show:
        plt.show()

    return fig


def save_calibration_pdfs(
    config_dir: "str | Path | None" = None,
    setup_name: "str | None" = None,
    output_dir: "str | Path | None" = None,
) -> list[str]:
    """Save one PDF calibration chart per setup to output_dir.

    Parameters
    ----------
    config_dir:
        msw_configs directory.  Resolved from machine config if None.
    setup_name:
        Plot only this setup; plots all setups if None or empty.
    output_dir:
        Directory for PDFs.  Defaults to the current working directory.

    Returns
    -------
    List of absolute paths to saved PDF files.
    """
    from datetime import datetime

    import yaml

    from murineshiftwork.logic.machine_config import resolve_config_dir

    config_dir = Path(config_dir) if config_dir else Path(resolve_config_dir())
    output_dir = Path(output_dir or ".").expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    setups_dir = config_dir / "setups"
    yaml_files = (
        [setups_dir / f"{setup_name}.yaml"]
        if setup_name
        else sorted(setups_dir.glob("*.yaml"))
    )

    dt_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved: list[str] = []

    for yf in yaml_files:
        if not yf.exists():
            logging.warning(f"Setup YAML not found: {yf}")
            continue
        with open(yf) as f:
            raw = yaml.safe_load(f) or {}
        sname = raw.get("name", yf.stem)
        if not raw.get("calibrations", {}).get("bpod_valve"):
            logging.info(f"No bpod_valve calibration in '{sname}', skipping")
            continue
        try:
            fig = plot_setup_valve_calibrations(
                config_dir=config_dir,
                setup_name=sname,
                save_fig=False,
                show=False,
            )
            out = output_dir / f"{sname}--{dt_str}.pdf"
            fig.savefig(out, format="pdf", bbox_inches="tight")
            plt.close(fig)
            saved.append(str(out))
            logging.info(f"Saved calibration PDF: {out}")
        except Exception as exc:
            logging.warning(f"Failed to plot calibration for '{sname}': {exc}")

    return saved


# Back-compat alias
CalibrationDataWater = CalibrationDataLiquid
