import logging
import time
from pathlib import Path

from pybpodapi.protocol import Bpod, StateMachine

from murineshiftwork.hardware.bpod import BpodFactory
from murineshiftwork.hardware.bpod.ttl import add_trial_onset_ttl
from murineshiftwork.hardware.stimulation import Stimulation
from murineshiftwork.logic.barcode import (
    BARCODE_FIRST_STATE_NAME,
    BarcodeTTL,
    barcode_config_from_settings,
    inject_barcode_states,
)
from murineshiftwork.logic.config.ini import deep_merge
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner
from murineshiftwork.namespace.manifest import append_subprotocol, finalize_subprotocol
from murineshiftwork.namespace.msw_files import msw_file
from murineshiftwork.readers.io import save_trial_data


class OptoTaggingRecord:
    """Per-subprotocol trial record. Each protocol writes its own JSONL file."""

    def __init__(self, session_file_path: str, protocol_name: str):
        session_dir = Path(session_file_path).parent
        session_basename = Path(session_file_path).name
        self.proto_dir_name = f"{session_basename}__{protocol_name}"
        proto_dir = session_dir / self.proto_dir_name
        proto_dir.mkdir(exist_ok=True)
        self.proto_base = str(proto_dir / f"{session_basename}_{protocol_name}")
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
        save_trial_data(self.trial_data, str(msw_file(self.proto_base, "df.jsonl")))
        logging.debug(f"Saved protocol data to {self.proto_base}")

    @property
    def filename(self) -> str:
        return (
            f"{self.proto_dir_name}/{Path(msw_file(self.proto_base, 'df.jsonl')).name}"
        )


class Task(TaskRunner):
    _bnc_channel_trial_onset = Bpod.OutputChannels.BNC1
    _bnc_channel_stimulation = Bpod.OutputChannels.BNC2
    _stim: "Stimulation | None" = None

    def stop(self):
        self.continue_task = False
        if self._stim is not None:
            import contextlib

            with contextlib.suppress(Exception):
                self._stim.off()

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
        session_basename = session_paths["session_basename"]
        conductor.initialize_acquisition(
            acquisition_path=str(
                Path(session_paths["session_folder_relative"])
                / f"{session_basename}__{protocol_name}"
            ),
            acquisition_name=f"{session_basename}_{protocol_name}",
        )
        conductor.start_preview()
        conductor.start_recording()
        time.sleep(warmup_s)

    def _reopen_bpod(
        self, session_folder: str, protocol_name: str, session_basename: str
    ) -> None:
        """Close the current Bpod session and open a fresh one scoped to this protocol."""
        serial_port = self.input_kwargs.get("serial_port_bpod", "")
        proto_dir = Path(session_folder) / f"{session_basename}__{protocol_name}"
        proto_dir.mkdir(exist_ok=True)
        self.bpod.close_safely()
        self.bpod = BpodFactory(
            serial_port=serial_port,
            workspace_path=str(proto_dir),
            session_name=f"{session_basename}_{protocol_name}.msw",
        )
        self.bpod.open()
        logging.debug("Bpod reopened for protocol %r → %s", protocol_name, proto_dir)

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
        session_paths = self.input_kwargs["session_paths"]
        session_file_path = session_paths["session_file_path"]
        session_folder = session_paths["session_folder"]
        session_basename = session_paths["session_basename"]

        barcode_cfg = barcode_config_from_settings(task_settings)
        barcoder = BarcodeTTL(barcode_cfg)

        for proto_idx, (protocol_name, protocol_config) in enumerate(
            stimulation_protocols.items()
        ):
            if not self.continue_task:
                break

            self._reopen_bpod(session_folder, protocol_name, session_basename)

            record = OptoTaggingRecord(session_file_path, protocol_name)

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
            self._stim = stim

            if record_video and conductor is not None:
                self._start_protocol_video(conductor, protocol_name)

            trial_index = 0
            bv_start = bv_end = None
            proto_status = "aborted"
            try:
                # Protocol-start barcode
                bv_start, bwt, timing_seq = barcoder.prepare()
                append_subprotocol(
                    session_folder,
                    protocol_name,
                    record.filename,
                    barcode_start=bv_start,
                )
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
                        barcode_value=bv_start,
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

                # Protocol-end barcode — skip if session was aborted mid-trial
                if not self.continue_task:
                    logging.info(
                        f"Protocol {protocol_name!r}: aborted, skipping end barcode."
                    )
                else:
                    try:
                        bv_end, bwt_end, timing_seq_end = barcoder.prepare()
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
                        proto_status = "complete"
                        logging.info(f"Protocol {protocol_name!r}: end barcode sent.")
                    except Exception:
                        logging.warning(
                            f"Protocol {protocol_name!r}: end barcode failed.",
                            exc_info=True,
                        )
            finally:
                self._stim = None
                stim.disconnect()
                finalize_subprotocol(
                    session_folder,
                    protocol_name,
                    barcode_end=bv_end,
                    status=proto_status,
                )
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
