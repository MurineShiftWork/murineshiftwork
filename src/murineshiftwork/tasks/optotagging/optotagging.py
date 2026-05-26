import logging
import time

from pybpodapi.protocol import Bpod, StateMachine
from ttl_barcoder.core.barcode_ttl import BarcodeTTL

from murineshiftwork.hardware.bpod.ttl import add_trial_onset_ttl
from murineshiftwork.logic.barcode import (
    BARCODE_FIRST_STATE_NAME,
    barcode_config_from_settings,
    inject_barcode_states,
    prepare_barcode,
)
from murineshiftwork.logic.config.ini import deep_merge
from murineshiftwork.logic.io import save_trial_data
from murineshiftwork.logic.stimulation import Stimulation
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner
from murineshiftwork.namespace.msw_files import msw_file


class OptoTaggingRecord:
    def __init__(self, out_path=None):
        self.out_path = out_path
        self.trial_data: list = []

    def update(
        self,
        trial_index=None,
        trial_data=None,
        barcode_value=None,
        barcode_wall_time=None,
        protocol=None,
    ):
        first_state_name = str(list(trial_data["States timestamps"].keys())[0]).lower()
        trial_type = (
            "barcode"
            if first_state_name.startswith(BARCODE_FIRST_STATE_NAME)
            else "task"
        )
        trial_data["info"] = {
            "trial_type": trial_type,
            "trial_index": trial_index,
            "protocol": protocol,
            "barcode_value": barcode_value,
            "barcode_wall_time": barcode_wall_time,
        }
        self.trial_data.append(trial_data)

    def save(self):
        save_trial_data(self.trial_data, str(msw_file(self.out_path, "jsonl")))
        logging.debug(f"Saved session data to {self.out_path}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()


class Task(TaskRunner):
    _bnc_channel_trial_onset = Bpod.OutputChannels.BNC1
    _bnc_channel_stimulation = Bpod.OutputChannels.BNC2

    def _start_protocol_video(
        self, conductor, protocol_name: str, warmup_s: float = 5.0
    ):
        """Initialize acquisition path, preview and start recording for one protocol.

        Protocols land directly under the acquisition root so they are siblings of the
        ephys session: subject/acquisition/protocol_name — not subject/acquisition/session/protocol_name.
        warmup_s must exceed the camera's min_warmup_before_recording (2 s on npxb) plus
        network round-trip, so the first barcode fires after frame TTL pulses have started.
        """
        session_paths = self.input_kwargs["session_paths"]
        _session = session_paths["session_basename"]
        _subject = session_paths["subject"]
        _is_child = self.input_kwargs.get("_is_child_session_to")
        # When running as a child of an ephys acquisition, place protocols directly
        # under the acquisition name — not under a session subdir.
        base = f"{_subject}/{_is_child}" if _is_child else f"{_subject}/{_session}"
        conductor.initialize_acquisition(
            acquisition_path=f"{base}/{protocol_name}",
            acquisition_name=f"{_session}_{protocol_name}",
        )
        conductor.start_preview()
        conductor.start_recording()
        time.sleep(warmup_s)

    def run(self) -> None:
        task_settings = self.input_kwargs["settings.task.patched"]
        devices = self.input_kwargs.get("devices") or {}
        pulsepal_handle = devices.get("pulsepal") if isinstance(devices, dict) else None
        serial_port_pulsepal = (
            None
            if pulsepal_handle is not None
            else (
                self.input_kwargs.get("serial_port_pulsepal")
                or task_settings.get("serial_port_pulsepal", "/dev/ttyACM1")
            )
        )

        stimulation_defaults = task_settings.get("stimulation_defaults", {})
        stimulation_protocols = task_settings.get("stimulation", {})
        conductor = self.input_kwargs.get("conductor")

        barcode_cfg = barcode_config_from_settings(task_settings)
        barcoder = BarcodeTTL(barcode_cfg)

        record = OptoTaggingRecord(
            out_path=self.input_kwargs["session_paths"]["session_file_path"]
        )

        for protocol_name, protocol_config in stimulation_protocols.items():
            if not self.continue_task:
                break

            params = deep_merge(stimulation_defaults, protocol_config or {})
            n_trials = int(params.pop("n_trials", 50))
            iti = float(params.pop("iti", 1.0))
            record_video = bool(params.pop("record_video", False))
            pulse_train_duration = float(params.get("pulse_train_duration", 1))

            logging.info(
                f"Protocol {protocol_name!r}: {n_trials} trials, iti={iti}s, "
                f"record_video={record_video}"
            )

            stim = Stimulation(port=serial_port_pulsepal, in_dict=params)
            stim.connect(handle=pulsepal_handle)

            if record_video and conductor is not None:
                self._start_protocol_video(conductor, protocol_name)

            trial_index = 0
            try:
                # Protocol-start barcode
                bv, bwt, timing_seq = prepare_barcode(barcoder)
                sma = StateMachine(bpod=self.bpod)
                sma = inject_barcode_states(
                    sma,
                    timing_seq,
                    self._bnc_channel_trial_onset,
                    last_state_name="exit",
                )
                try:
                    self.bpod.send_state_machine(sma)
                    _barcode_ok = self.bpod.run_state_machine(sma)
                except OSError as exc:
                    logging.error(
                        f"Bpod serial connection lost before protocol {protocol_name!r}"
                        f" — USB I/O error: {exc}"
                    )
                    break
                if not _barcode_ok:
                    logging.warning(
                        f"Protocol {protocol_name!r}: no data on start barcode."
                    )
                else:
                    record.update(
                        trial_index=trial_index,
                        trial_data=self.bpod.session.current_trial.export(),
                        barcode_value=bv,
                        barcode_wall_time=bwt,
                        protocol=protocol_name,
                    )
                    record.save()
                trial_index += 1

                while self.continue_task and trial_index <= n_trials:
                    sma = StateMachine(bpod=self.bpod)
                    sma = add_trial_onset_ttl(
                        sma=sma,
                        ttl_pulse_duration=0.001,
                        bnc_channel=self._bnc_channel_trial_onset,
                        next_state="pulses",
                    )
                    sma = add_trial_onset_ttl(
                        sma=sma,
                        state_name_tuple=("pulses", "pulse_off"),
                        ttl_pulse_duration=pulse_train_duration,
                        bnc_channel=self._bnc_channel_stimulation,
                        next_state="iti",
                    )
                    sma.add_state(
                        state_name="iti",
                        state_timer=iti,
                        state_change_conditions={Bpod.Events.Tup: "exit"},
                        output_actions=[],
                    )

                    try:
                        self.bpod.send_state_machine(sma)
                        if not self.bpod.run_state_machine(sma):
                            logging.warning(
                                f"Protocol {protocol_name!r}: no data on trial {trial_index}. "
                                "Terminating protocol."
                            )
                            break
                    except OSError as exc:
                        logging.error(
                            f"Bpod serial connection lost on trial #{trial_index}"
                            f" — USB I/O error: {exc}"
                        )
                        break

                    _t_bpod_done = time.perf_counter()

                    record.update(
                        trial_index=trial_index,
                        trial_data=self.bpod.session.current_trial.export(),
                        barcode_value=None,
                        barcode_wall_time=None,
                        protocol=protocol_name,
                    )
                    record.save()

                    _compute_ms = (time.perf_counter() - _t_bpod_done) * 1000
                    logging.info(
                        f"Protocol {protocol_name!r} trial {trial_index:4d} | "
                        f"compute {_compute_ms:.0f}ms"
                    )
                    trial_index += 1

                # Protocol-end barcode
                try:
                    bv_end, bwt_end, timing_seq_end = prepare_barcode(barcoder)
                    sma_end = StateMachine(bpod=self.bpod)
                    sma_end = inject_barcode_states(
                        sma_end,
                        timing_seq_end,
                        self._bnc_channel_trial_onset,
                        last_state_name="exit",
                    )
                    self.bpod.send_state_machine(sma_end)
                    self.bpod.run_state_machine(sma_end)
                    record.update(
                        trial_index=trial_index,
                        trial_data=self.bpod.session.current_trial.export(),
                        barcode_value=bv_end,
                        barcode_wall_time=bwt_end,
                        protocol=protocol_name,
                    )
                    record.save()
                    logging.info(f"Protocol {protocol_name!r}: end barcode sent.")
                except Exception:
                    logging.warning(
                        f"Protocol {protocol_name!r}: end barcode failed.",
                        exc_info=True,
                    )
            finally:
                stim.disconnect()
                logging.info(f"Protocol {protocol_name!r}: stimulation disconnected.")

            if record_video and conductor is not None:
                conductor.stop_acquisition()
                time.sleep(1)

        logging.debug("Exiting Task.")


def run_task(**args_dict):
    task_settings = args_dict.get("settings.task.patched", {})
    stimulation_defaults = task_settings.get("stimulation_defaults", {})
    stimulation_protocols = task_settings.get("stimulation", {})

    needs_video = stimulation_defaults.get("record_video", False) or any(
        (p or {}).get("record_video", False) for p in stimulation_protocols.values()
    )

    conductor = None
    if needs_video:
        from murineshiftwork.hardware.camera.client import make_camera_client

        conductor = make_camera_client(
            cameras_config=args_dict.get("cameras_config"),
            config_file_camera=args_dict.get("config_file_camera", ""),
            output_dir=args_dict.get("out_path", ""),
        )
        if conductor is None:
            raise RuntimeError(
                "record_video is set but no camera config found. "
                "Pass --config-file-camera or configure cameras: in setup YAML, "
                "or set record_video: false."
            )
        conductor.start()
        conductor.setup_agents()

    # _is_child_session_to passed through as a plain kwarg so Task.run() can build
    # the per-protocol acquisition path without needing to reconstruct it.
    args_dict["_is_child_session_to"] = args_dict.get("is_child_session_to")
    args_dict["conductor"] = conductor
    args_dict["auto_start"] = False

    with TaskProcess(**args_dict) as tp:
        tp.run_task()
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

    if conductor is not None:
        conductor.stop()


if __name__ == "__main__":
    print("main")
