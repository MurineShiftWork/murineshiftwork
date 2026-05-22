import logging
import time
from multiprocessing import Queue

from pybpodapi.state_machine import StateMachine
from ttl_barcoder.core.barcode_ttl import BarcodeTTL

from murineshiftwork.logic.barcode import (
    barcode_config_from_settings,
    inject_barcode_states,
    prepare_barcode,
)
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner
from murineshiftwork.tasks.sequence.online_plotting import OnlinePlottingForSeq
from murineshiftwork.tasks.sequence.task_objects import TaskControl


class Task(TaskRunner):
    def run(self):
        task_settings = self.input_kwargs["settings.task.patched"]

        task_settings["subject"] = self.input_kwargs.get("subject", "unknown")
        task_settings.setdefault(
            "session_paths", self.input_kwargs.get("session_paths", {})
        )

        barcode_cfg = barcode_config_from_settings(task_settings)
        barcoder = BarcodeTTL(barcode_cfg)
        bnc_channel = getattr(
            self.bpod.OutputChannels,
            f"BNC{task_settings['HARDWARE_BNC_TRIAL_START']}",
        )

        task_control = TaskControl(bpod=self.bpod, task_settings=task_settings)
        self.bpod.softcode_handler_function = task_control.softcode_handler

        trial_index = 0
        max_trials = task_settings["n_max_trials"]
        _stop_reward_ul = float(task_settings.get("stop_reward_ul", 1000.0))
        _stop_trials = int(task_settings.get("stop_trials", 500))
        _stop_time_min = float(task_settings.get("stop_time_min", 60.0))
        _stop_level = int(task_settings.get("start_level", 1)) + int(
            task_settings.get("stop_level_delta", 15)
        )
        _warned_stop: dict[str, bool] = {
            "reward": False,
            "trials": False,
            "time": False,
            "level": False,
        }

        while self.continue_task and trial_index < max_trials:
            barcode_value = None
            barcode_wall_time = None

            if trial_index == 0 and not task_settings["testing"]:
                barcode_value, barcode_wall_time, timing_seq = prepare_barcode(barcoder)
                sma = StateMachine(bpod=self.bpod)
                sma = inject_barcode_states(
                    sma, timing_seq, bnc_channel, last_state_name="exit"
                )
            else:
                sma = task_control.draw_next_trial()

            try:
                self.bpod.send_state_machine(sma)
                if not self.bpod.run_state_machine(sma):
                    logging.warning(f"No data on trial #{trial_index}. Terminating.")
                    self.input_kwargs["objects"]["kill_queue"].put(True)
                    break
            except OSError as exc:
                logging.error(
                    f"Bpod serial connection lost on trial #{trial_index}"
                    f" — USB I/O error: {exc}"
                )
                self.input_kwargs["objects"]["kill_queue"].put(True)
                break

            trial_data = self.bpod.session.current_trial.export()
            task_control.update(
                trial_index=trial_index,
                trial_data=trial_data,
                barcode_value=barcode_value,
                barcode_wall_time=barcode_wall_time,
            )
            task_control.save()

            info = trial_data.get("info", {})
            if info.get("trial_type") == "task":
                _liq = info.get("liquid_ul_cumulative", 0.0)
                _t_min = trial_data.get("Trial start timestamp", 0) / 60.0
                if (
                    not _warned_stop["reward"]
                    and _stop_reward_ul > 0
                    and _liq >= _stop_reward_ul
                ):
                    _warned_stop["reward"] = True
                    logging.warning(
                        "Stop criterion — reward: %.0f µL ≥ %.0f µL (1 ml)",
                        _liq,
                        _stop_reward_ul,
                    )
                if (
                    not _warned_stop["time"]
                    and _stop_time_min > 0
                    and _t_min >= _stop_time_min
                ):
                    _warned_stop["time"] = True
                    logging.warning(
                        "Stop criterion — time: %.1f min ≥ %.0f min (1 h)",
                        _t_min,
                        _stop_time_min,
                    )
                if (
                    not _warned_stop["trials"]
                    and _stop_trials > 0
                    and task_control._session_task_trials >= _stop_trials
                ):
                    _warned_stop["trials"] = True
                    logging.warning(
                        "Stop criterion — trials: %d task trials ≥ %d (+ %d no-response)",
                        task_control._session_task_trials,
                        _stop_trials,
                        task_control._session_no_response_count,
                    )
                if (
                    not _warned_stop["level"]
                    and _stop_level > 0
                    and task_control.current_level >= _stop_level
                ):
                    _warned_stop["level"] = True
                    logging.warning(
                        "Stop criterion — level: %d ≥ %d (%d levels above session start %d)",
                        task_control.current_level,
                        _stop_level,
                        task_settings.get("stop_level_delta", 15),
                        task_settings.get("start_level", 1),
                    )

            if task_settings.get("show_live_plot", True) and trial_index > 0:
                if info.get("trial_type") == "task":
                    self.input_kwargs["objects"]["data_queue"].put(
                        {
                            "trial_index": task_control.trial_index,
                            "outcome": task_control.last_outcome,
                            "level": task_control.current_level,
                            "level_at_trial": info.get(
                                "level", task_control.current_level
                            ),
                            "perf_buffer_mean": info.get("perf_buffer_mean", 0.0),
                            "perf_perfect_mean": info.get("perf_perfect_mean", 0.0),
                            "is_perfect": info.get("is_perfect", False),
                            "trial_time_s": trial_data.get("Trial start timestamp", 0),
                            "reward_count_trial": info.get("reward_count_trial", 0),
                            "liquid_ul_trial": info.get("liquid_ul_trial", 0.0),
                            "liquid_ul_cumulative": info.get(
                                "liquid_ul_cumulative", 0.0
                            ),
                            "poke_events": info.get("poke_events", []),
                            "transition_times": info.get("transition_times", []),
                            "sequence_duration_s": info.get("sequence_duration_s"),
                        }
                    )

            trial_index += 1

        # Session-end barcode: fires after last trial completes (including on Ctrl+C stop),
        # before Bpod closes. Provides a second alignment anchor for clock-drift correction.
        if not task_settings["testing"]:
            try:
                bv_end, bwt_end, timing_seq_end = prepare_barcode(barcoder)
                sma_end = StateMachine(bpod=self.bpod)
                sma_end = inject_barcode_states(
                    sma_end,
                    timing_seq_end,
                    bnc_channel,
                    last_state_name="exit",
                )
                self.bpod.send_state_machine(sma_end)
                self.bpod.run_state_machine(sma_end)
                trial_data_end = self.bpod.session.current_trial.export()
                task_control.update(
                    trial_index=trial_index,
                    trial_data=trial_data_end,
                    barcode_value=bv_end,
                    barcode_wall_time=bwt_end,
                )
                task_control.save()
                logging.info("Session-end barcode sent.")
            except (OSError, Exception) as _exc:
                import serial

                if isinstance(_exc, (OSError, serial.SerialException)):
                    logging.debug(
                        f"Session-end barcode skipped (port already dead): {_exc}"
                    )
                else:
                    logging.warning(
                        "Session-end barcode failed to send.", exc_info=True
                    )

        task_control.save_session_end()
        self.input_kwargs["objects"]["kill_queue"].put(True)
        logging.debug("Exiting Task.")


def run_task(**args_dict):
    """Entry point called by the MSW CLI: ``msw run -s <subject> -t sequence``."""
    dq: Queue = Queue()
    kq: Queue = Queue()
    args_dict.update({"objects": {"data_queue": dq, "kill_queue": kq}})
    args_dict.update({"auto_start": False})

    task_settings = args_dict.get("settings.task.patched", {})

    with TaskProcess(**args_dict) as tp:
        # Online plot (separate process)
        if task_settings.get("show_live_plot", True):
            plotting = OnlinePlottingForSeq(
                session_name=tp.session_paths.get("session_basename", ""),
                subject=args_dict.get("subject", ""),
                setup=args_dict.get("setup", "")
                or args_dict.get("metadata", {}).get("setup", ""),
                data_queue=dq,
                kill_queue=kq,
                n_max_trials=task_settings.get("n_max_trials", 1500),
                n_levels=50,
                progression_threshold=task_settings.get("progression_threshold", 0.9),
                regression_threshold=task_settings.get("regression_threshold", 0.2),
                sequence=list(task_settings.get("sequence", [])),
                port_colors=list(task_settings.get("port_colors", [])),
                poke_ymax_s=task_settings.get("online_plot_poke_ymax_s") or None,
                poke_xmax_s=float(task_settings.get("online_plot_poke_xmax_s", 6.0)),
                xlim_trials=int(task_settings.get("online_plot_xlim_trials", 100)),
                poke_log_scale=bool(
                    task_settings.get("online_plot_poke_log_scale", True)
                ),
                first_poke_offset_s=float(
                    task_settings.get("online_plot_first_poke_offset_s", 0.5)
                ),
                stop_reward_ul=float(task_settings.get("stop_reward_ul", 1000.0)),
                stop_trials=int(task_settings.get("stop_trials", 500)),
                stop_time_min=float(task_settings.get("stop_time_min", 60.0)),
                stop_level_delta=int(task_settings.get("stop_level_delta", 15)),
                start_level=int(task_settings.get("start_level", 1)),
            )
            plotting.start()

        time.sleep(1)

        tp.run_task()
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

        kq.put(True)
        time.sleep(1)


if __name__ == "__main__":
    run_task()
