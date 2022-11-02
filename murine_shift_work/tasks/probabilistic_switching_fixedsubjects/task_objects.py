import json
import logging
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine
from stage_controller.move_interface import MoveInterface

from murine_shift_work.logic.calibration import CalibrationDataSound
from murine_shift_work.logic.calibration import CalibrationDataWater
from murine_shift_work.logic.maths import ExponentialMovingAverage
from murine_shift_work.logic.maths import withprob
from murine_shift_work.logic.sounds import StereoSound
from murine_shift_work.logic.specific_state_machines import add_trial_onset_ttl
from murine_shift_work.tasks.probabilistic_switching_fixedsubjects.stage_config import (
    config_for_all_stages,
)


class TaskControl(object):
    bpod = None
    sound = None
    sound_delay_correction = 0

    task_settings = {}
    trial_data = []
    save_path_data = None

    # Task progress
    trial_index = 0
    block_number = 0
    block_trial_number = 0
    reward_number = 0

    # Block switches -- length range: 10 - 20+
    min_block_length = 15
    mean_neutral_block_length = 25  # 10 trials difference to min block length
    min_trials_post_criterion = 5
    trials_post_criterion = 0
    max_block_length = 50

    criterion_contrast_blocks = (
        0.5  # task_settings.CRITERION_CONTRAST_BLOCKS  # 0.6
    )
    criterion_neutral_blocks = 0.2
    criterion_tau = 5
    criterion_block_switch_reached = False
    block_switch_hazard_rate = 1 / (
        mean_neutral_block_length - min_block_length
    )

    moving_average = ExponentialMovingAverage(
        tau=criterion_tau, init_value=0.0
    )  # 0=sides coded as -1/1 for left/right, so init value has to be center == 0

    probabilities = [(80, 0), (0, 80)]  # task_settings.PROBABILITIES
    block_probability_index = None
    probability_left = 0
    probability_right = 0

    next_trial_choice_outcome_left = 0
    next_trial_choice_outcome_right = 0
    next_trial_give_stop_signal = 0
    stop_signal_delay = None
    stop_trial_success = None

    initiation_hold_time = None
    is_forced_exploration_trial = False

    last_choice = 0
    last_rewarded = 0
    last_punish = 0
    last_stop = 0

    def __init__(self, bpod=None, save_path_data=None, task_settings=None):
        super(TaskControl, self).__init__()

        if not bpod:
            raise ValueError("Required input argument: bpod")
        self.bpod = bpod

        self.save_path_data = (
            Path(self.bpod.workspace_path) / self.bpod.session_name
            if not save_path_data
            else save_path_data
        )
        print(f"Running session: {Path(self.save_path_data).name}")
        logging.info(self.task_settings)

        self.task_settings = task_settings
        self.probabilities = self.task_settings["probabilities"]
        self.criterion_contrast_blocks = self.task_settings[
            "criterion_contrast_blocks"
        ]

        # fixme 1: implement loading of presets for basic PS (no stop)
        #  and stop signal PS (adaptive stops, probabilities all 1/0 for analysis simplicity)
        # fixme 2: use hardware params for go/stop signal generation

        self.calibration_sound = CalibrationDataSound(
            file_path=self.task_settings["calibration_file_sound"]
        )
        self.sound = StereoSound(sound_device=StereoSound.default_sound_device)
        # self.sound_go = self.sound.register_new_sound(frequency=5000, duration=.1, amplitude=.2)
        self.sound_stop = self.sound.register_new_sound(
            frequency=-1, duration=0.4, amplitude=0.5
        )

        self.sound_delay_correction = (
            self.calibration_sound.calculate_sound_delay_correction()
        )
        self.calibration_water = CalibrationDataWater(
            file_path=Path(
                "~/.murineshiftwork/calibration.water.default.csv"
            ).expanduser(),  # self.task_settings["calibration_file_water"]
        )
        self.valve_times_dict = (
            self.calibration_water.water_volume_to_valve_time(
                valves=self.task_settings["HARDWARE_VALVES_FOR_WATER"],
                target_volume=self.task_settings["reward_amount_ul"],
                s_to_ms=1,
            )
        )
        logging.info(
            f"VALVES: {self.valve_times_dict} "
            f"FOR {self.task_settings['reward_amount_ul']} "
            f"on VALVE IDs: {self.task_settings['HARDWARE_VALVES_FOR_WATER']}"
        )

        axes_names = tuple(
            config_for_all_stages["stage_tower_setup_1"].get("axes").keys()
        )
        # serial_port = task_settings.get() # "/dev/ttyUSB0"
        stage_config = config_for_all_stages["stage_tower_setup_1"]
        serial_port = task_settings.get("serial_port_stage")
        self.stage = MoveInterface(
            axes_names=axes_names,
            serial_port=serial_port,
            stage_config=stage_config,
        )
        self.stage.save_position_as_known(
            "front"
        )  # fixme: determine front in pre-protocol instead of rely on experimenter's awareness
        self.stage.move_to_known_position(
            "back"
        )  # move back before first trial
        self.stage.write_config(
            config_path=self.save_path_data.parent
            / ".".join([self.save_path_data.name, "settings", "stage", "yaml"])
        )
        logging.info(self.stage)

        self.MOVE_TO_FRONT = 15
        self.MOVE_TO_BACK = 25

        # Persist task settings -> todo: refactor to method
        with open(str(self.save_path_data) + ".settings.task.json", "w") as f:
            json.dump(self.task_settings, f, indent=4, sort_keys=True)

        logging.debug("Task control class created.")
        self.bpod.softcode_handler_function = self.softcode_handler

    def softcode_handler(self, softcode=None):
        logging.debug(f"SOFT CODE RECEIVED: {softcode}")

        self.sound.execute_sound_handler(
            sound_code=softcode, raise_errors=False
        )

        if softcode == self.MOVE_TO_FRONT:
            logging.debug("MOVING TO FRONT")
            self.stage.move_to_known_position("front")
        if softcode == self.MOVE_TO_BACK:
            logging.debug("MOVING TO BACK")
            self.stage.move_to_known_position("back")

    def switch_block(self):
        logging.debug("Resetting block.")
        self.block_number += 1
        self.block_trial_number = 0
        self.trials_post_criterion = 0
        self.criterion_block_switch_reached = False

        # Reset moving average bias
        if self.task_settings["reset_bias_on_block_switch"]:
            self.moving_average.reset()

        # Choose first block type to motivate subject
        if self.trial_index < 2 and self.task_settings["first_block_easy"]:
            pdiffs = np.abs(np.diff(self.probabilities))
            pdiffmax = np.max(pdiffs)
            range_for_prob = [i for i, p in enumerate(pdiffs) if p == pdiffmax]
        else:
            range_for_prob = np.arange(self.probabilities.__len__())

        # Exclude current block from choice of __read_next_frame block type
        if self.task_settings["block_switch_to_different_block_type"]:
            next_probs_allowed = list(
                set(range_for_prob) - set([self.block_probability_index])
            )
        else:
            next_probs_allowed = list(set(range_for_prob))

        # Draw new block type
        if len(next_probs_allowed) == 1:
            self.block_probability_index = next_probs_allowed[0]
        else:
            self.block_probability_index = next_probs_allowed[
                random.randint(0, len(next_probs_allowed) - 1)
            ]

        # Assign new probabilities
        new_prob = self.probabilities[self.block_probability_index]

        if any([x > 1 for x in new_prob]):
            logging.debug(
                f"Given probability proportions {new_prob}. Now converting to percentages (x/100)"
            )
            self.probability_left, self.probability_right = [
                x / 100 for x in new_prob
            ]
        else:
            self.probability_left, self.probability_right = new_prob

        logging.info(
            f"New block #{self.block_number} after trial #{self.trial_index} with probabilities {self.probability_left}/{self.probability_right}"
        )

        # TODO: block update rules fixed trials vs criterion

    def update(self, trial_index=None, trial_data=None):
        self.trial_index = trial_index
        # trial_data is: bpod start ts, trial start ts, trial end ts, state and event ts

        first_state_name = str(
            list(trial_data["States timestamps"].keys())[0]
        ).lower()
        if self.trial_index < 1 and first_state_name.startswith("pulse"):
            # IF TTL TRIAL
            self.switch_block()
            trial_data["info"] = {
                "trial_type": "ttl",
                "trial_index": self.trial_index,
            }
            return self.trial_data.append(trial_data)

        # IF TASK TRIAL
        self.block_trial_number += 1

        st = trial_data["States timestamps"]
        times_left = st["choice_left"][0]
        times_right = st["choice_right"][0]

        # TODO: USE THESE VARIABLES FOR OUTCOME EVALUATION FOR ANALYSIS DATA MATRIX
        # outcome_left_reward = (
        #     st["outcome_left_reward"][0]
        #     if "outcome_left_reward" in st.keys()
        #     else [np.nan]
        # )
        # outcome_right_reward = (
        #     st["outcome_right_reward"][0]
        #     if "outcome_right_reward" in st.keys()
        #     else [np.nan]
        # )
        # outcome_left_punish = (
        #     st["outcome_left_punish"][0]
        #     if "outcome_left_punish" in st.keys()
        #     else [np.nan]
        # )
        # outcome_right_punish = (
        #     st["outcome_right_punish"][0]
        #     if "outcome_right_punish" in st.keys()
        #     else [np.nan]
        # )

        if not np.isnan(np.array(times_left)).any():
            self.last_choice = -1
        elif not np.isnan(np.array(times_right)).any():
            self.last_choice = 1
        else:
            self.last_choice = np.nan  # timeout / no response

        # Update last choice
        self.moving_average.update(latest_sample=self.last_choice)
        # Update last outcome: reward/neutral/punish
        if (
            self.next_trial_choice_outcome_left and self.last_choice == -1
        ) or (self.next_trial_choice_outcome_right and self.last_choice == 1):
            self.reward_number += 1
            self.last_rewarded = 1
            self.last_punish = 0
        else:
            self.last_rewarded = 0
            if (
                self.next_trial_choice_outcome_left < 0
                and self.last_choice == -1
            ) or (
                self.next_trial_choice_outcome_right < 0
                and self.last_choice == 1
            ):
                print("PUNISHED")
                self.last_punish = 1
            else:
                self.last_punish = 0

        self.last_stop = self.next_trial_give_stop_signal

        if self.next_trial_give_stop_signal:
            self.stop_trial_success = None  # TODO: no outcome or center port -> success, otherwise failed and punished

        trial_data["info"] = {
            "trial_type": "task",
            "trial_index": trial_index,
            "block_trial_number": self.block_trial_number,
            "block_number": self.block_number,
            "block_type_index": self.block_probability_index,
            "block_type_values": self.probabilities[
                self.block_probability_index
            ],
            "moving_average": self.moving_average(),
            "choice": self.last_choice,
            "rewarded": self.last_rewarded,  # fixme: this only works as long as no punishments introduced
            "reward_available_left": self.next_trial_choice_outcome_left,  # fixme: same: only for non-punish/non-stop task
            "reward_available_right": self.next_trial_choice_outcome_right,  # fixme: same
            "trials_post_criterion": self.trials_post_criterion,
            "criterion_block_switch_reached": self.criterion_block_switch_reached,
            "stop_trial": self.next_trial_give_stop_signal,
            "stop_signal_delay": self.stop_signal_delay,
            "stop_trial_success": self.stop_trial_success,
            "initiation_delay_actual": self.initiation_hold_time,
            "forced_exploration_trial": self.is_forced_exploration_trial,
        }
        trial_data["analysis"] = {}
        # TODO: add analysis variables: init hold time, time from init to withdrawal, travel time outbound,
        #  travel time inbound from last trial, nr failed init attempts

        self.trial_data.append(trial_data)

        if self.trial_index < 1:
            return

        item_end = "| "
        print(
            f"[T={round(trial_data['Trial start timestamp']/60, 1): >4} min] {item_end}"
            f"Trial#{self.trial_index: >4} {item_end}"
            f"Block#{self.block_number:>2} {item_end}"
            f"BlockTrial#{self.block_trial_number:>4} {item_end}"
            f"Choice: {self.last_choice:>3}. {item_end}"
            f"Pref: {np.round(self.moving_average(),2):>5}. {item_end}"
            f"Reward: {self.reward_number:>4} "
            f"({round(self.task_settings['reward_amount_ul']*self.reward_number, 2):>4}uL). {item_end}"
            f"Crit: {self.trials_post_criterion:>2}"
        )

        # Check for block criterion
        neutral_block_bias = (
            np.abs(self.moving_average()) <= self.criterion_neutral_blocks
        )

        if self.criterion_block_switch_reached:
            self.trials_post_criterion += 1
        elif self.block_trial_number >= self.min_block_length and (
            (
                self.probability_left == self.probability_right
                and neutral_block_bias
            )
            or (
                self.probability_left > self.probability_right
                and self.moving_average() < -self.criterion_contrast_blocks
            )
            or (
                self.probability_right > self.probability_left
                and self.moving_average() > self.criterion_contrast_blocks
            )
            or (
                self.block_trial_number
                >= self.max_block_length - self.min_trials_post_criterion
            )
        ):
            self.criterion_block_switch_reached = True

        # Check for block switch (trial based)
        if self.block_trial_number >= self.min_block_length and (
            (
                self.probability_left == self.probability_right
                and withprob(self.block_switch_hazard_rate)
            )
            or self.trials_post_criterion >= self.min_trials_post_criterion
        ):
            self.switch_block()

        self.save()

    def make_forced_exploration_sma(self, next_choice_option=None):
        if next_choice_option < 0:  # LEFT
            left_valve = self.task_settings["HARDWARE_VALVES_FOR_WATER"][0]
            output_action_only_valve = [
                (Bpod.OutputChannels.Valve, left_valve)
            ]
            valve_outcome = self.valve_times_dict[left_valve]
            port_nr = left_valve
            side_name = "left"
        else:
            right_valve = self.task_settings["HARDWARE_VALVES_FOR_WATER"][1]
            output_action_only_valve = [
                (Bpod.OutputChannels.Valve, right_valve)
            ]
            valve_outcome = self.valve_times_dict[right_valve]
            port_nr = right_valve
            side_name = "right"

        output_actions__side_ready = [
            (
                eval(f"Bpod.OutputChannels.PWM{port_nr}"),
                self.task_settings["HARDWARE_PORT_LIGHT_INTENSITY"],
            ),
        ]
        state_name_choice = f"choice_{side_name}"
        state_change_condition = {
            eval(f"Bpod.Events.Port{port_nr}In"): state_name_choice
        }

        logging.warning(
            f"{self.trial_index} -- Making forced choice to side: {next_choice_option}"
        )
        sma = StateMachine(self.bpod)
        # TTL
        sma = add_trial_onset_ttl(
            sma=sma,
            ttl_pulse_duration=self.task_settings["ttl_pulse_duration"],
            bnc_channel=eval(
                f"Bpod.OutputChannels.BNC{self.task_settings['HARDWARE_BNC_TRIAL_START']}"
            ),
            next_state="side_ready",
        )
        # WAITING
        sma.add_state(
            state_name="side_ready",
            state_timer=20,
            state_change_conditions={
                **state_change_condition,
                Bpod.Events.Tup: "exit",
            },
            output_actions=output_actions__side_ready + [],
        )
        sma.add_state(
            state_name="choice_left",
            state_timer=valve_outcome,
            state_change_conditions={Bpod.Events.Tup: "final"},
            output_actions=output_action_only_valve + [],
        )
        sma.add_state(
            state_name="choice_right",
            state_timer=valve_outcome,
            state_change_conditions={Bpod.Events.Tup: "final"},
            output_actions=output_action_only_valve + [],
        )

        sma.add_state(
            state_name="final",
            state_timer=self.task_settings["state_duration_final"],
            state_change_conditions={
                Bpod.Events.Port1Out: "exit",
                Bpod.Events.Port2Out: "exit",
                Bpod.Events.Port3Out: "exit",
                Bpod.Events.Tup: "exit",
            },
            output_actions=[],
        )

        return sma

    def draw_next_trial(self):
        n_back_crit = self.task_settings["forced_choice_threshold"]
        if self.block_trial_number >= n_back_crit:
            key = "choice"
            td_info = [
                td["info"]
                for td in self.trial_data
                if td and key in td["info"]
            ]
            choice_vector = [c[key] for c in td_info if key in c.keys()]
            unique_choices = np.unique(choice_vector[-n_back_crit:])
            unique_choices_n_back = unique_choices.__len__()

            if unique_choices_n_back == 1:
                self.is_forced_exploration_trial = True
                return self.make_forced_exploration_sma(
                    next_choice_option=-1 * unique_choices[-1]
                )
            else:
                self.is_forced_exploration_trial = (
                    True  # fixme: this is wrong ??
                )

        if self.block_probability_index is None:
            self.switch_block()

        # side probabilities ?
        self.next_trial_choice_outcome_left = (
            1 if withprob(self.probability_left) else 0
        )
        self.next_trial_choice_outcome_right = (
            1 if withprob(self.probability_right) else 0
        )
        # is stop trial ?
        self.next_trial_give_stop_signal = self.task_settings[
            "use_stop_trials"
        ] and withprob(self.task_settings["stop_trial_proportion"])
        if self.next_trial_give_stop_signal:
            # if stopped, also punish ?
            self.next_trial_choice_outcome_left = (
                -1
                if self.task_settings["punish_stop_trials"]
                and withprob(
                    self.task_settings["punish_stop_trials_proportion"]
                )
                else 0
            )
            self.next_trial_choice_outcome_right = (
                -1
                if self.task_settings["punish_stop_trials"]
                and withprob(
                    self.task_settings["punish_stop_trials_proportion"]
                )
                else 0
            )

            if self.stop_signal_delay is None:
                self.stop_signal_delay = self.task_settings[
                    "stop_trial_delay_initial"
                ]

            # TODO: STOP signal adaptive testing here: change of stop signal delay ++ self.sound_delay_correction

        # If is last trial in block, make sure it's rewarded
        if self.trials_post_criterion >= self.min_trials_post_criterion - 1:
            if self.probability_left:
                self.next_trial_choice_outcome_left = 1
            if self.probability_right:
                self.next_trial_choice_outcome_right = 1
            logmsg = (
                f"LAST TRIAL in block: forcing reward on non-zero reward choices. "
                f"Left={self.next_trial_choice_outcome_left}. "
                f"Right={self.next_trial_choice_outcome_right}"
            )
            logging.debug(logmsg)

        # Stimulation
        if self.task_settings["use_stimulation"] and withprob(
            self.task_settings["stimulation_trial_proportion"]
        ):
            pass
            # TODO: implement STIMULATION trials:
            #  connect pulsepal, upload stim settings, add BNC event to output actions

        # make SMA
        sma = self.make_state_machine()
        logging.debug("New trial drawn")

        # from importlib import reload
        # task_settings = reload(task_settings)
        return sma

    def make_state_machine(self):
        logging.debug(
            f"Making new StateMachine. Outcomes are "
            f"left={self.next_trial_choice_outcome_left}, "
            f"right={self.next_trial_choice_outcome_right}"
        )

        # LIGHTS - if intensity - for chosen ports (center/side)
        output_actions__center_ready = []
        # output_actions__center_delay = []  # FIXME: STILL USED ??
        output_actions__side_ready = []
        if self.task_settings["HARDWARE_PORT_LIGHT_INTENSITY"]:
            if "center" in self.task_settings["HARDWARE_PORT_LIGHT_PORTS"]:
                output_actions__center_ready = [
                    (
                        Bpod.OutputChannels.PWM2,
                        self.task_settings["HARDWARE_PORT_LIGHT_INTENSITY"],
                    )
                ]
                # output_actions__center_delay = output_actions__center_ready # FIXME: STILL USED ??
            if "side" in self.task_settings["HARDWARE_PORT_LIGHT_PORTS"]:
                output_actions__side_ready = [
                    (
                        Bpod.OutputChannels.PWM1,
                        self.task_settings["HARDWARE_PORT_LIGHT_INTENSITY"],
                    ),
                    (
                        Bpod.OutputChannels.PWM3,
                        self.task_settings["HARDWARE_PORT_LIGHT_INTENSITY"],
                    ),
                ]

        initiation_hold_time = self.task_settings["delay_until_center_init"]
        if isinstance(initiation_hold_time, list):
            initiation_hold_time = np.asarray(initiation_hold_time)
            if len(initiation_hold_time) > 2:
                step = initiation_hold_time[2] * 1000  # sec to msec
            else:
                step = 1

            hold_time_range = (
                np.abs(np.diff(initiation_hold_time[:2])) * 1000
            )  # sec to msec
            available_hold_times = np.linspace(
                initiation_hold_time[0],
                initiation_hold_time[1],
                int(np.round(hold_time_range / step)) + 1,
                endpoint=True,
            )
            available_hold_times = np.round(
                available_hold_times, 3
            )  # ms rounding
            initiation_hold_time = available_hold_times[
                np.random.randint(0, len(available_hold_times))
            ]
            logging.debug(
                f"-- Drawn new initiation hold time of {initiation_hold_time}s."
            )
            self.initiation_hold_time = initiation_hold_time

        # SMA
        sma = StateMachine(bpod=self.bpod)

        state_center_ready = "center_ready"
        sma = add_trial_onset_ttl(
            sma=sma,
            ttl_pulse_duration=self.task_settings["ttl_pulse_duration"],
            bnc_channel=eval(
                f"Bpod.OutputChannels.BNC{self.task_settings['HARDWARE_BNC_TRIAL_START']}"
            ),
            next_state=state_center_ready,  # FIXME: NEXT STATE MOVES STAGE
        )
        #             sma.add_state(
        #                 state_name="leave",
        #                 state_timer=0,
        #                 state_change_conditions={"Tup": "exit"},
        #                 output_actions=[("SoftCode", self.sound.sound_stop_code)],  fixme: SOFT CODE
        #             )

        # TRIAL
        state_side_ready = "side_ready"
        sma.add_state(
            state_name=state_center_ready,
            state_timer=0,
            state_change_conditions={Bpod.Events.Tup: state_side_ready},
            output_actions=output_actions__center_ready
            + [("SoftCode", self.MOVE_TO_FRONT)],
        )
        # INIT long enough -> proceed. pulled out too early -> back to center_ready
        # sma.add_state(
        #     state_name="center_initiating",
        #     state_timer=initiation_hold_time,
        #     state_change_conditions={
        #         Bpod.Events.Port2Out: "center_ready",  # ABORTED
        #         Bpod.Events.Tup: "side_ready",
        #     },  # CONTINUE
        #     output_actions=output_actions__center_delay,
        # )

        # TRAVEL to side -> wait for entry
        if self.next_trial_give_stop_signal:
            delay_until_stop_signal = (
                self.stop_signal_delay - self.sound_delay_correction
            )
            delay_until_side_timeout = (
                self.task_settings["side_timeout_for_stopping"]
                - delay_until_stop_signal
            )

            print(
                f"-- STOP trial with delay={round(delay_until_stop_signal,2)}s "
                f"({self.stop_signal_delay}-{self.sound_delay_correction}) "
                f"and timeout after {delay_until_side_timeout}s"
            )
            # STOP signal:
            #       mouse moving
            #       side ready + wait for delay
            #       side ready + trigger sound
            #           side in -> AIR
            #           no entry -> __read_next_frame trial
            #
            # SWITCH signal:
            #       mouse moving
            #       side ready + wait for delay
            #       side ready + trigger sound
            #           side in -> AIR
            #           center light -> center in -> reward

            sma.add_state(
                state_name=state_side_ready,
                state_timer=delay_until_stop_signal,
                state_change_conditions={
                    # Bpod.Events.Port1In: "choice_left",
                    # Bpod.Events.Port3In: "choice_right",
                    Bpod.Events.Tup: "side_ready_post_stop",
                },
                output_actions=output_actions__side_ready,
            )
            sma.add_state(
                state_name="side_ready_post_stop",
                state_timer=delay_until_side_timeout,
                state_change_conditions={
                    Bpod.Events.Port1In: "choice_left",
                    # Bpod.Events.Port2In: "exit",
                    Bpod.Events.Port3In: "choice_right",
                    Bpod.Events.Tup: "exit",
                },
                output_actions=output_actions__side_ready
                + [("SoftCode", self.sound_stop)],
            )
        else:  # REGULAR TRIAL
            sma.add_state(
                state_name=state_side_ready,
                state_timer=self.task_settings["delay_until_side_timeout"],
                state_change_conditions={
                    Bpod.Events.Port1In: "choice_left",
                    Bpod.Events.Port3In: "choice_right",
                    Bpod.Events.Tup: "final",
                },
                output_actions=output_actions__side_ready,
            )

        # OUTCOMES: LEFT  --  Encoding:  0=unrewarded, 1=rewarded, -1=punish with air
        # note: stop signal outcomes set to 0 in __read_next_frame-trial
        if self.next_trial_choice_outcome_left > 0:  # REWARD
            left_valve = self.task_settings["HARDWARE_VALVES_FOR_WATER"][0]
            output_action_left_valve = [
                (Bpod.OutputChannels.Valve, left_valve)
            ]
            valve_left_outcome = self.valve_times_dict[left_valve]
        elif self.next_trial_choice_outcome_left < 0:  # PUNISH
            output_action_left_valve = [
                (
                    Bpod.OutputChannels.Valve,
                    self.task_settings["HARDWARE_VALVES_FOR_AIR"][0],
                )
            ]
            valve_left_outcome = self.task_settings["punish_air_duration"]
        else:  # == 0
            output_action_left_valve = []
            valve_left_outcome = 0

        # OUTCOMES: RIGHT  --  Encoding:  0=unrewarded, 1=rewarded, -1=punish with air
        if self.next_trial_choice_outcome_right > 0:  # REWARD
            right_valve = self.task_settings["HARDWARE_VALVES_FOR_WATER"][1]
            output_action_right_valve = [
                (Bpod.OutputChannels.Valve, right_valve)
            ]
            valve_right_outcome = self.valve_times_dict[right_valve]
        elif self.next_trial_choice_outcome_right < 0:  # PUNISH
            output_action_right_valve = [
                (
                    Bpod.OutputChannels.Valve,
                    self.task_settings["HARDWARE_VALVES_FOR_AIR"][1],
                )
            ]
            valve_right_outcome = self.task_settings["punish_air_duration"]
        else:  # == 0
            output_action_right_valve = []
            valve_right_outcome = 0

        outcome_codes = {-1: "punish", 0: "neutral", 1: "reward"}
        outcome_doc_left = f"outcome_left_{outcome_codes[self.next_trial_choice_outcome_left]}"
        outcome_doc_right = f"outcome_right_{outcome_codes[self.next_trial_choice_outcome_right]}"

        sma.add_state(
            state_name="choice_left",
            state_timer=valve_left_outcome,
            state_change_conditions={Bpod.Events.Tup: outcome_doc_left},
            output_actions=output_action_left_valve + [],
        )
        sma.add_state(
            state_name="choice_right",
            state_timer=valve_right_outcome,
            state_change_conditions={Bpod.Events.Tup: outcome_doc_right},
            output_actions=output_action_right_valve + [],
        )

        # Outcome documentation
        sma.add_state(
            state_name=outcome_doc_left,
            state_timer=2,  # if valve_left_outcome else 0,
            state_change_conditions={Bpod.Events.Tup: "final"},
            output_actions=[] + [("SoftCode", 78)],
        )
        sma.add_state(
            state_name=outcome_doc_right,
            state_timer=2,  # if valve_right_outcome else 0,
            state_change_conditions={Bpod.Events.Tup: "final"},
            output_actions=[] + [("SoftCode", 77)],
        )
        # Cleanup
        sma.add_state(
            state_name="final",
            state_timer=self.task_settings["state_duration_final"],
            state_change_conditions={
                Bpod.Events.Port1Out: "iti",
                Bpod.Events.Port2Out: "iti",
                Bpod.Events.Port3Out: "iti",
                Bpod.Events.Tup: "iti",
            },
            output_actions=[] + [("SoftCode", self.MOVE_TO_BACK)],
        )
        ITI = 4
        sma.add_state(
            state_name="iti",
            state_timer=ITI,
            state_change_conditions={
                Bpod.Events.Tup: "exit",
            },
            output_actions=[] + [("SoftCode", 88)],
        )
        # END
        return sma

    def save(self):
        logging.debug("Saving task control data..")
        dt = time.time()
        df = pd.DataFrame(self.trial_data)
        df.to_pickle(str(self.save_path_data) + ".df.pkl")
        logging.debug(f"Saved data in {np.round(time.time()-dt,2)}s.")

    def on_exit(self):
        # retract spout stage
        # self.softcode_handler(softcode=self.MOVE_TO_BACK)
        # logging.debug("Moved stage BACK on exit")

        # save data
        self.save()

    def __del__(self):
        self.softcode_handler(softcode=self.MOVE_TO_BACK)
        logging.debug("Moved stage BACK on exit")

        self.save()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.softcode_handler(softcode=self.MOVE_TO_BACK)
        logging.debug("Moved stage BACK on exit")

        self.save()
