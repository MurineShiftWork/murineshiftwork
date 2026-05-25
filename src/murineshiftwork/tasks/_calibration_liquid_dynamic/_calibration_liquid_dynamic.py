"""Adaptive water-valve calibration with a serial weighing scale.

Unlike the fixed-grid protocol (_calibration_liquid_static), this
task determines the number of valve pulses per measurement point dynamically
(based on expected volume and scale noise) and adds new opening-time points
adaptively until the target delivery range is covered.
"""

import logging
import math
import random
import time
import warnings

import numpy as np
from pybpodapi.exceptions.bpod_error import BpodErrorException
from scipy.optimize import OptimizeWarning, curve_fit
from tqdm import tqdm

from murineshiftwork.hardware.bpod.valve import make_sma_for_drop_of_water
from murineshiftwork.logic.calibration import (
    CalibrationDataWater,
    _exponential_function,
    flag_outlier_points,
)
from murineshiftwork.logic.config import update_valve_calibration
from murineshiftwork.logic.scale import make_scale
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner

# ---------------------------------------------------------------------------
# Pure helper functions (no hardware dependencies — unit-testable)


def _compute_n_pulses(
    expected_ul: float,
    scale_noise_g: float,
    min_snr: float,
    min_pulses: int,
    max_pulses: int,
) -> int:
    """Return pulses needed so weight signal >= min_snr * scale_noise.

    Signal  = n_pulses * expected_ul / 1000  [g]
    Noise   = scale_noise_g                  [g]
    Require: signal >= min_snr * noise
    => n >= min_snr * scale_noise_g * 1000 / expected_ul
    """
    if expected_ul <= 0:
        return max_pulses
    needed = math.ceil(min_snr * scale_noise_g * 1000.0 / expected_ul)
    return max(min_pulses, min(needed, max_pulses))


def _estimate_ul(
    open_s: float,
    measured_times: list,
    measured_ul: list,
) -> float:
    """Estimate µL/drop at open_s from current measurements.

    Uses exponential fit when ≥3 points exist, nearest-point linear scaling
    with 2 points, and a conservative default of 1.0 µL with 0 or 1 points.
    """
    if not measured_times:
        return 1.0
    if len(measured_times) < 2:
        t0, u0 = measured_times[0], measured_ul[0]
        return max(0.1, u0 * (open_s / t0)) if t0 > 0 else 1.0

    times_arr = np.asarray(measured_times, dtype=float)
    ul_arr = np.asarray(measured_ul, dtype=float)

    if len(measured_times) >= 3:
        try:
            mask = ul_arr > 0
            ts, us = times_arr[mask], ul_arr[mask]
            s_span = float(ts.max() - ts.min()) if len(ts) >= 2 else 1.0
            ul_min, ul_max = float(us.min()), float(us.max())
            b0 = np.log(ul_max / ul_min) / s_span if s_span > 0 and ul_min > 0 else 5.0
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", OptimizeWarning)
                popt, _ = curve_fit(
                    _exponential_function,
                    ts,
                    us,
                    p0=[ul_min, b0, 0.0],
                    bounds=([0.0, 0.0, -np.inf], [np.inf, np.inf, np.inf]),
                    maxfev=5000,
                )
            return float(max(0.1, _exponential_function(open_s, *popt)))
        except Exception:
            pass

    # Linear fallback
    coeffs = np.polyfit(times_arr, ul_arr, 1)
    return float(max(0.1, np.polyval(coeffs, open_s)))  # type: ignore[call-overload]


def _suggest_additional_times(
    measured_times: list,
    measured_ul: list,
    min_ul: float,
    max_ul: float,
    time_min_s: float,
    time_max_s: float,
    n_target: int = 5,
) -> list:
    """Suggest new opening times needed to cover [min_ul, max_ul].

    Returns an empty list when coverage is already satisfied.
    Strategy:
    - Fit curve; find opening times corresponding to min_ul and max_ul
    - If those boundary times are outside the currently measured range,
      add boundary points
    - If the interior is sparse, add interpolated midpoints
    """
    if len(measured_times) < 2:
        return []

    times_arr = np.asarray(measured_times, dtype=float)
    ul_arr = np.asarray(measured_ul, dtype=float)

    # Build best-available predictor
    try:
        mask = ul_arr > 0
        ts, us = times_arr[mask], ul_arr[mask]
        s_span = float(ts.max() - ts.min()) if len(ts) >= 2 else 1.0
        ul_min, ul_max = float(us.min()), float(us.max())
        b0 = np.log(ul_max / ul_min) / s_span if s_span > 0 and ul_min > 0 else 5.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", OptimizeWarning)
            popt, _ = curve_fit(
                _exponential_function,
                ts,
                us,
                p0=[ul_min, b0, 0.0],
                bounds=([0.0, 0.0, -np.inf], [np.inf, np.inf, np.inf]),
                maxfev=5000,
            )

        def fit_fn(t):
            return float(_exponential_function(t, *popt))
    except Exception:
        coeffs = np.polyfit(times_arr, ul_arr, 1)

        def fit_fn(t):
            return float(np.polyval(coeffs, t))

    new_times: list[float] = []

    # --- Lower boundary ---
    ul_at_min_time = fit_fn(float(times_arr.min()))
    if ul_at_min_time > min_ul * 1.3:
        # Lowest measured time still delivers more than target min → go lower
        candidate = round(float(times_arr.min()) * 0.6, 4)
        if candidate >= time_min_s and candidate not in measured_times:
            new_times.append(candidate)

    # --- Upper boundary ---
    ul_at_max_time = fit_fn(float(times_arr.max()))
    if ul_at_max_time < max_ul * 0.7:
        # Highest measured time still delivers less than target max → go higher
        candidate = round(min(float(times_arr.max()) * 1.5, time_max_s), 4)
        if candidate not in measured_times:
            new_times.append(candidate)

    # --- Interior density ---
    # Count how many measured points land (by predicted fit) in [min_ul, max_ul]
    in_range = [
        t
        for t, u in zip(measured_times, measured_ul)
        if min_ul * 0.9 <= u <= max_ul * 1.1
    ]
    if len(in_range) < n_target:
        deficit = n_target - len(in_range)
        # Spread new candidate times evenly across the current range
        t_lo = float(times_arr.min())
        t_hi = float(times_arr.max())
        candidates = np.linspace(t_lo, t_hi, deficit + 2)[1:-1]
        for c in candidates:
            rc = round(float(c), 4)
            if rc not in measured_times and rc not in new_times:
                new_times.append(rc)

    return new_times


# ---------------------------------------------------------------------------
# Task


class Task(TaskRunner):
    """Adaptive valve-calibration task."""

    def run(self) -> None:
        s = self.input_kwargs.get("settings.task.patched", {})

        valves = list(s.get("VALVES_TO_CALIBRATE", [1, 3]))
        target_range_ul = list(s.get("TARGET_RANGE_UL", [0.5, 8.0]))
        min_ul, max_ul = float(target_range_ul[0]), float(target_range_ul[1])

        initial_times_s = list(s.get("INITIAL_OPENING_TIMES_S", []))
        time_min_s = float(s.get("OPENING_TIME_MIN_S", 0.005))
        time_max_s = float(s.get("OPENING_TIME_MAX_S", 0.150))
        n_initial = int(s.get("N_INITIAL_POINTS", 5))

        inter_pulse_s = float(s.get("INTER_PULSE_INTERVAL_S", 0.150))
        settle_s = float(s.get("SETTLE_TIME_S", 2.5))

        scale_noise_g = float(s.get("SCALE_NOISE_G", 0.05))
        min_snr = float(s.get("MIN_SNR", 10))
        min_pulses = int(s.get("MIN_PULSES", 50))
        max_pulses = int(s.get("MAX_PULSES", 1000))

        max_adaptive_rounds = int(s.get("MAX_ADAPTIVE_ROUNDS", 3))
        n_target = int(s.get("COVERAGE_N_POINTS_TARGET", 5))
        outlier_sigma = float(s.get("OUTLIER_SIGMA_THRESHOLD", 2.5))
        config_dir = self.input_kwargs.get("config_dir", "")
        setup_name = self.input_kwargs.get("setup", "")
        force_save = bool(s.get("force_save_calibration", False))

        # --- Calibration plan overview ---
        if initial_times_s:
            plan_desc = f"manual grid: {sorted(set(round(float(t), 4) for t in initial_times_s))}"
        else:
            plan_desc = (
                f"anchor protocol — max={time_max_s:.4f}s, "
                f"then linear estimate for {min_ul} µL, "
                f"then {n_initial} interior points"
            )
        logging.info(
            f"\n{'=' * 60}\n"
            f"Adaptive calibration plan\n"
            f"  Valves:       {', '.join(str(v) for v in valves)}\n"
            f"  Target range: {min_ul}–{max_ul} µL\n"
            f"  Protocol:     {plan_desc}\n"
            f"  Settle time:  {settle_s} s | Scale noise: {scale_noise_g} g | SNR target: {min_snr}\n"
            f"  Max rounds:   {max_adaptive_rounds} adaptive\n"
            f"{'=' * 60}"
        )

        scale = self.input_kwargs.get("scale") or make_scale(
            serial_port=self.input_kwargs.get("serial_port_scale", ""),
            scale_type=self.input_kwargs.get("scale_type", "hx711"),
            baudrate=self.input_kwargs.get("scale_baudrate"),
        )
        scale.start()
        self._tare_verified(scale, max_retries=2, threshold_g=1.0)

        calibration = CalibrationDataWater(
            file_path=self.input_kwargs.get("calibration_file_liquid") or None
        )

        try:
            for valve_id in valves:
                if not self.continue_task:
                    break
                try:
                    self._calibrate_valve(
                        valve_id=valve_id,
                        calibration=calibration,
                        scale=scale,
                        initial_times_s=initial_times_s,
                        time_min_s=time_min_s,
                        time_max_s=time_max_s,
                        n_initial=n_initial,
                        min_ul=min_ul,
                        max_ul=max_ul,
                        inter_pulse_s=inter_pulse_s,
                        settle_s=settle_s,
                        scale_noise_g=scale_noise_g,
                        min_snr=min_snr,
                        min_pulses=min_pulses,
                        max_pulses=max_pulses,
                        max_adaptive_rounds=max_adaptive_rounds,
                        n_target=n_target,
                        outlier_sigma=outlier_sigma,
                    )
                except Exception as exc:
                    logging.error(f"Valve {valve_id}: calibration aborted — {exc}.")
                    break

                self._write_valve_to_yaml(
                    valve_id, calibration, config_dir, setup_name, force_save
                )
        finally:
            logging.debug(f"\n{str(calibration)}\n")
            calibration.save(overwrite=True)

    def _tare_verified(
        self, scale, max_retries: int = 2, threshold_g: float = 1.0
    ) -> None:
        """Tare and verify the post-tare reading is within threshold of zero.

        Retries up to max_retries times; logs a warning if never within range
        so the operator knows to check scale placement before trusting results.
        """
        for attempt in range(max_retries + 1):
            scale.tare()
            post_tare = scale.read_weight_blocking()
            logging.info(f"Scale ready. Post-tare weight: {post_tare:.4f} g")
            if abs(post_tare) <= threshold_g:
                return
            logging.warning(
                f"Post-tare weight {post_tare:.4f} g exceeds ±{threshold_g} g — "
                + (
                    "retrying tare"
                    if attempt < max_retries
                    else "proceeding anyway; check scale placement and surface stability"
                )
            )

    # ------------------------------------------------------------------

    def _write_valve_to_yaml(
        self, valve_id, calibration, config_dir, setup_name, force_save
    ):
        if not (config_dir and setup_name and not setup_name.startswith("unknown_")):
            return
        try:
            new_cal = calibration.to_valve_calibration(valve_id)
        except ValueError as exc:
            logging.warning(f"Valve {valve_id}: cannot build ValveCalibration — {exc}")
            return
        is_valid, reason = new_cal.validate()
        logging.info(
            f"Valve {valve_id}: validation {'PASS' if is_valid else 'FAIL'} — {reason}"
        )
        written = update_valve_calibration(
            config_dir=config_dir,
            setup_name=setup_name,
            valve_id=valve_id,
            new_calibration=new_cal,
            force=force_save,
        )
        if written:
            logging.info(
                f"Valve {valve_id}: written to {setup_name}.yaml ({len(new_cal.points)} points)"
            )
        else:
            logging.warning(
                f"Valve {valve_id}: NOT written — validation failed. "
                "Re-run with force_save_calibration=true to override."
            )

    # ------------------------------------------------------------------

    def _calibrate_valve(
        self,
        valve_id,
        calibration,
        scale,
        initial_times_s,
        time_min_s,
        time_max_s,
        n_initial,
        min_ul,
        max_ul,
        inter_pulse_s,
        settle_s,
        scale_noise_g,
        min_snr,
        min_pulses,
        max_pulses,
        max_adaptive_rounds,
        n_target,
        outlier_sigma,
    ) -> None:
        # time_min_s is a hard floor — the protocol never issues pulses shorter than this.
        measured_times: list[float] = []
        measured_ul: list[float] = []

        if initial_times_s:
            # Expert / manual mode: use the provided grid directly.
            logging.info(
                f"\n{'=' * 55}\nCalibrating valve {valve_id}"
                f"  |  target range: {min_ul}–{max_ul} µL\n{'=' * 55}"
            )
            pending = sorted(set(round(float(t), 4) for t in initial_times_s))
        else:
            t_max = round(float(time_max_s), 4)

            # Anchor 1: measure at time_max_s — highest SNR; seeds linear estimate.
            ul_max = self._measure_point(
                valve_id,
                t_max,
                calibration,
                scale,
                measured_times,
                measured_ul,
                inter_pulse_s,
                settle_s,
                scale_noise_g,
                min_snr,
                min_pulses,
                max_pulses,
            )
            measured_times.append(t_max)
            measured_ul.append(ul_max)

            # Anchor 2: linear extrapolation → t where volume ≈ min_ul.
            # Binary-search upward (max 3 steps) when the estimate undershoots.
            if ul_max >= min_ul:
                t_est = round(max(float(time_min_s), (min_ul / ul_max) * t_max), 4)
            else:
                logging.warning(
                    f"Valve {valve_id}: {t_max:.4f}s delivers only {ul_max:.3f} µL/drop "
                    f"(below {min_ul} µL target min) — using max as lower anchor"
                )
                t_est = t_max

            for _attempt in range(3):
                if t_est >= t_max:
                    break
                ul_est = self._measure_point(
                    valve_id,
                    t_est,
                    calibration,
                    scale,
                    measured_times,
                    measured_ul,
                    inter_pulse_s,
                    settle_s,
                    scale_noise_g,
                    min_snr,
                    min_pulses,
                    max_pulses,
                )
                measured_times.append(t_est)
                measured_ul.append(ul_est)
                if ul_est >= min_ul:
                    break
                new_t = round(t_est + (t_max - t_est) * 0.5, 4)
                logging.warning(
                    f"Valve {valve_id}: {t_est:.4f}s → {ul_est:.3f} µL/drop "
                    f"< {min_ul} µL — stepping up to {new_t:.4f}s"
                )
                t_est = new_t

            effective_min_s = measured_times[-1]
            logging.info(
                f"\n{'=' * 55}\nCalibrating valve {valve_id}"
                f"  |  target range: {min_ul}–{max_ul} µL"
                f"  |  anchors: {effective_min_s:.4f}s – {t_max:.4f}s\n{'=' * 55}"
            )

            # Interior points between anchors; endpoints already measured.
            interior = np.linspace(effective_min_s, t_max, n_initial + 2)[1:-1]
            pending = [round(float(t), 4) for t in interior]

        for round_idx in range(max_adaptive_rounds + 1):
            new_this_round = [t for t in pending if t not in measured_times]
            if not new_this_round:
                logging.info(f"Valve {valve_id}: no new times — coverage satisfied.")
                break

            random.shuffle(new_this_round)
            for open_s in new_this_round:
                if not self.continue_task:
                    return
                for _attempt in range(2):
                    try:
                        ul_per_drop = self._measure_point(
                            valve_id,
                            open_s,
                            calibration,
                            scale,
                            measured_times,
                            measured_ul,
                            inter_pulse_s,
                            settle_s,
                            scale_noise_g,
                            min_snr,
                            min_pulses,
                            max_pulses,
                        )
                        break
                    except BpodErrorException:
                        if _attempt == 0:
                            logging.warning(
                                f"Valve {valve_id} | open={open_s:.4f}s: "
                                "Bpod error — retrying in 2 s..."
                            )
                            time.sleep(2)
                        else:
                            raise
                    except ValueError as exc:
                        logging.warning(
                            f"Valve {valve_id} | open={open_s:.4f}s: {exc} — skipping point"
                        )
                        ul_per_drop = None
                        break
                if ul_per_drop is None:
                    continue
                measured_times.append(open_s)
                measured_ul.append(ul_per_drop)

            if round_idx < max_adaptive_rounds:
                suggestions = _suggest_additional_times(
                    measured_times,
                    measured_ul,
                    min_ul,
                    max_ul,
                    time_min_s,
                    time_max_s,
                    n_target,
                )
                if not suggestions:
                    logging.info(
                        f"Valve {valve_id}: range {min_ul}–{max_ul} µL covered "
                        f"after round {round_idx} ({len(measured_times)} points)."
                    )
                    break
                logging.info(
                    f"Valve {valve_id}: round {round_idx + 1} — adding "
                    f"{len(suggestions)} time(s): {[f'{t:.4f}s' for t in suggestions]}"
                )
                pending = suggestions

        # Outlier retry — re-measure flagged points with 2× pulses; to_valve_calibration
        # uses .last() per opening time so the retry replaces the original row.
        if len(measured_times) >= 3:
            outlier_mask, residuals = flag_outlier_points(
                measured_times, measured_ul, outlier_sigma
            )
            sigma_val = float(np.std(residuals)) or 1.0
            if outlier_mask.any():
                for i, (is_out, t, ul, res) in enumerate(
                    zip(outlier_mask, measured_times, measured_ul, residuals)
                ):
                    if not is_out or not self.continue_task:
                        continue
                    logging.warning(
                        f"[Valve {valve_id}] Outlier: open_s={t:.4f}s "
                        f"measured={ul:.3f} µL/drop "
                        f"(residual={res:+.3f} µL, {abs(res) / sigma_val:.1f}σ) "
                        f"— re-measuring with 2× pulses"
                    )
                    try:
                        new_ul = self._measure_point(
                            valve_id,
                            t,
                            calibration,
                            scale,
                            measured_times,
                            measured_ul,
                            inter_pulse_s,
                            settle_s,
                            scale_noise_g,
                            min_snr,
                            min(min_pulses * 2, max_pulses),
                            max_pulses,
                        )
                        measured_ul[i] = new_ul
                    except ValueError as exc:
                        logging.warning(
                            f"[Valve {valve_id}] Retry for {t:.4f}s failed: {exc} — keeping original"
                        )
            else:
                logging.info(
                    f"Valve {valve_id}: no outliers detected (threshold {outlier_sigma}σ)."
                )

    def _measure_point(
        self,
        valve_id,
        open_s,
        calibration,
        scale,
        measured_times,
        measured_ul,
        inter_pulse_s,
        settle_s,
        scale_noise_g,
        min_snr,
        min_pulses,
        max_pulses,
    ) -> float:
        expected_ul = _estimate_ul(open_s, measured_times, measured_ul)
        n_pulses = _compute_n_pulses(
            expected_ul, scale_noise_g, min_snr, min_pulses, max_pulses
        )

        if n_pulses == max_pulses:
            logging.warning(
                f"Valve {valve_id} | open={open_s:.4f}s: n_pulses capped at {max_pulses} "
                f"(expected {expected_ul:.3f} µL/drop — may be near deadzone)"
            )
        logging.info(
            f"Valve {valve_id} | open={open_s:.4f}s | "
            f"~{expected_ul:.2f} µL/drop expected | {n_pulses} pulses"
        )

        weight_before = scale.read_weight_blocking()

        for _ in tqdm(
            range(n_pulses), leave=False, desc=f"valve {valve_id} {open_s:.4f}s"
        ):
            if not self.continue_task:
                break
            sma = make_sma_for_drop_of_water(
                bpod=self.bpod,
                valve_opening_time=open_s,
                valve_ids=valve_id,
                inter_drop_interval=inter_pulse_s,
            )
            self.bpod.send_state_machine(sma)
            if not self.bpod.run_state_machine(sma):
                break

        time.sleep(settle_s)
        weight_g = round(scale.read_weight_blocking() - weight_before, 4)

        if weight_g < -scale_noise_g:
            raise ValueError(
                f"negative weight {weight_g:.4f} g at open={open_s:.4f}s "
                f"(load-cell drift or tare issue)"
            )

        ul_per_drop = round(weight_g * 1000.0 / n_pulses, 3)

        logging.info(
            f"Valve {valve_id} | open={open_s:.4f}s | "
            f"weight={weight_g:.4f} g | {ul_per_drop:.3f} µL/drop"
        )

        calibration.add_calibration_point(
            valve_id=valve_id,
            valve_opening_time=open_s,
            n_drops=n_pulses,
            inter_pulse_interval=inter_pulse_s,
            liquid_weight_g=weight_g,
        )
        return ul_per_drop


# ---------------------------------------------------------------------------


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()
    logging.info("Calibration task complete.")


if __name__ == "__main__":
    run_task()
