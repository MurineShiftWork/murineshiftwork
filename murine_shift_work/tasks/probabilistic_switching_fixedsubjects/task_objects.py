import json
import logging
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine
from one_axis_stage.interface import StageController
from one_axis_stage.interface import MoveInterface

from murine_shift_work.logic.barcode import BARCODE_FIRST_STATE_NAME
from murine_shift_work.logic.calibration import CalibrationDataSound
from murine_shift_work.logic.calibration import CalibrationDataWater
from murine_shift_work.logic.maths import ExponentialMovingAverage
from murine_shift_work.logic.maths import withprob
from murine_shift_work.io.trial_data import save_trial_data
from murine_shift_work.logic.misc import draw_jittered_trial_time
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
    max_block_length = 75

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
    last_forced_choice = 0

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
        self.max_block_length = self.task_settings.get(
            "max_block_length", self.max_block_length
        )
        self.criterion_contrast_blocks = self.task_settings[
            "criterion_contrast_blocks"
        ]

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
            file_path=task_settings["calibration_file_water"]
        )

        self.valve_times_dict = (
            self.calibration_water.water_volume_to_valve_time(
                valves=self.task_settings["HARDWARE_VALVES_FOR_WATER"],
                target_volume=float(self.task_settings["reward_amount_ul"]),
                s_to_ms=1,
            )
        )
        logging.info(
            f"VALVES: {self.valve_times_dict} "
            f"FOR {self.task_settings['reward_amount_ul']} "
            f"on VALVE IDs: {self.task_settings['HARDWARE_VALVES_FOR_WATER']}"
        )

        # axes_names = tuple(task_settings["settings.stage"].get("axes").keys())
        serial_port_stage = task_settings.get("serial_port_stage")
        # print("serial_port_stage", serial_port_stage)
        task_settings["settings.stage"]["connection"][
            "serial_port"
        ] = serial_port_stage  # fixme: shouldnt be necessaRY TO OVERWRITE
        self.stage = StageController.from_config(task_settings["settings.stage"])
        # self.move_interface = MoveInterface(controller=self.stage)
        #
        self.stage.small_increment = 20
        self.stage.large_increment = 40
        #
        # self.stage.save_as_known_position("front_center")
        print(self.stage.known_positions)
        self.stage.save_as_known_position("front")
        # fixme: determine front in pre-protocol instead of rely on experimenter's awareness
        print(self.stage.known_positions)

        self.stage.move_to_known_position(
            "back"
        )  # move back before first trial

        self.stage.save_config(
            config_file=self.save_path_data.parent
            / ".".join([self.save_path_data.name, "settings", "stage", "yaml"])
        )
        logging.info(self.stage)

        self.MOVE_TO_FRONT = 15
        self.MOVE_TO_BACK = 25

        self.stage_anti_bias_bool = self.task_settings.get(
            "stage_anti_bias_bool", False
        )
        self.stage_bias = 0
        self.stage_bias_max = self.task_settings.get("stage_anti_bias_max", 50)
        self.n_back_crit_bias = self.task_settings.get(
            "stage_anti_bias_n_back", 5
        )

        print("stage_anti_bias_bool", self.stage_anti_bias_bool)
        print("stage_bias_max", self.stage_bias_max)
        print("n_back_crit_bias", self.n_back_crit_bias)

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
        if (
            self.trial_index < 2
            and self.block_number == 1
            and self.task_settings["first_block_easy"]
        ):
            pdiffs = np.abs(np.diff(self.probabilities))
            pdiffmax = np.max(pdiffs)
            range_for_prob = [i for i, p in enumerate(pdiffs) if p == pdiffmax]
            print(f"BLOCK 1 drawn as {range_for_prob}")
        elif self.block_number == 2 and self.task_settings["first_block_easy"]:
            pdiffs = np.abs(np.diff(self.probabilities))
            pdiffmax = np.max(pdiffs)
            range_for_prob = [
                i
                for i, p in enumerate(pdiffs)
                if p == pdiffmax and i != self.block_probability_index
            ]
            print(f"BLOCK 2 drawn as {range_for_prob}")
        else:
            range_for_prob = np.arange(self.probabilities.__len__())
            print(f"BLOCK 2+ drawn as {range_for_prob}")

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

    def update(self, trial_index=None, trial_data=None, barcode_value=None, barcode_wall_time=None):
        self.trial_index = trial_index

        first_state_name = str(list(trial_data["States timestamps"].keys())[0])
        if first_state_name.lower() == BARCODE_FIRST_STATE_NAME.lower():
            if self.trial_index == 0:
                self.switch_block()  # initialise first block after session-start barcode
            trial_data["info"] = {
                "trial_type": "barcode",
                "trial_index": self.trial_index,
                "barcode_value": barcode_value,
                "barcode_wall_time": barcode_wall_time,
            }
            return self.trial_data.append(trial_data)

        # IF TASK TRIAL
        self.block_trial_number += 1

        st = trial_data["States timestamps"]
        times_left = st["choice_left"][0]
        times_right = st["choice_right"][0]

        # print(
        #     "states",
        #     st,
        # )
        # print(
        #     "ev",
        #     {k: v for k, v in trial_data["Events timestamps"].items() if "BNC" in k},
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
        self.last_forced_choice = self.is_forced_exploration_trial

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

        item_spacer = " | "
        print(
            f"[{round(trial_data['Trial start timestamp'] / 60, 1): >4}min]{item_spacer}"
            f"T#{self.trial_index: >4}{item_spacer}"
            f"B#{self.block_number:>2}{item_spacer}"
            f"BT#{self.block_trial_number:>4}{item_spacer}"
            f"Choice: {self.last_choice:>3}{item_spacer}"
            f"Pref: {np.round(self.moving_average(), 2):>5}{item_spacer}"
            f"Reward: {self.reward_number:>4} "
            f"({round(self.task_settings['reward_amount_ul'] * self.reward_number, 2):>4}uL).{item_spacer}"
            f"Crit: {self.trials_post_criterion:>2}{item_spacer}"
            f"Forced: {self.is_forced_exploration_trial} / "
            f"T until forced: {self.task_settings['forced_choice_threshold'] - self.block_trial_number}"
        )

        self.is_forced_exploration_trial = False

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

    # def make_forced_exploration_sma(self, next_choice_option=None):
    #     if next_choice_option < 0:  # LEFT
    #         left_valve = self.task_settings["HARDWARE_VALVES_FOR_WATER"][0]
    #         output_action_only_valve = [
    #             (Bpod.OutputChannels.Valve, left_valve)
    #         ]
    #         valve_outcome = self.valve_times_dict[left_valve]
    #         port_nr = left_valve
    #         side_name = "left"
    #     else:
    #         right_valve = self.task_settings["HARDWARE_VALVES_FOR_WATER"][1]
    #         output_action_only_valve = [
    #             (Bpod.OutputChannels.Valve, right_valve)
    #         ]
    #         valve_outcome = self.valve_times_dict[right_valve]
    #         port_nr = right_valve
    #         side_name = "right"
    #
    #     output_actions__side_ready = [
    #         (
    #             eval(f"Bpod.OutputChannels.PWM{port_nr}"),
    #             self.task_settings["HARDWARE_PORT_LIGHT_INTENSITY"],
    #         ),
    #     ]
    #     state_name_choice = f"choice_{side_name}"
    #     state_change_condition = {
    #         eval(f"Bpod.Events.Port{port_nr}In"): state_name_choice
    #     }
    #
    #     logging.warning(
    #         f"{self.trial_index} -- Making forced choice to side: {next_choice_option}"
    #     )
    #     sma = StateMachine(self.bpod)
    #     # TTL
    #     sma = add_trial_onset_ttl(
    #         sma=sma,
    #         ttl_pulse_duration=self.task_settings["ttl_pulse_duration"],
    #         bnc_channel=eval(
    #             f"Bpod.OutputChannels.BNC{self.task_settings['HARDWARE_BNC_TRIAL_START']}"
    #         ),
    #         next_state="side_ready",
    #     )
    #     # WAITING
    #     sma.add_state(
    #         state_name="side_ready",
    #         state_timer=20,
    #         state_change_conditions={
    #             **state_change_condition,
    #             Bpod.Events.Tup: "exit",
    #         },
    #         output_actions=output_actions__side_ready + [],
    #     )
    #     sma.add_state(
    #         state_name="choice_left",
    #         state_timer=valve_outcome,
    #         state_change_conditions={Bpod.Events.Tup: "final"},
    #         output_actions=output_action_only_valve + [],
    #     )
    #     sma.add_state(
    #         state_name="choice_right",
    #         state_timer=valve_outcome,
    #         state_change_conditions={Bpod.Events.Tup: "final"},
    #         output_actions=output_action_only_valve + [],
    #     )
    #
    #     sma.add_state(
    #         state_name="final",
    #         state_timer=self.task_settings["state_duration_final"],
    #         state_change_conditions={
    #             Bpod.Events.Port1Out: "exit",
    #             Bpod.Events.Port2Out: "exit",
    #             Bpod.Events.Port3Out: "exit",
    #             Bpod.Events.Tup: "exit",
    #         },
    #         output_actions=[],
    #     )
    #
    #     return sma

    def draw_next_trial(self):
        n_back_crit = self.task_settings["forced_choice_threshold"]
        key = "choice"
        td_info = [
            td["info"] for td in self.trial_data if td and key in td["info"]
        ]
        choice_vector = [c[key] for c in td_info if key in c.keys()]
        unique_choices = np.unique(choice_vector[-n_back_crit:])
        unique_choices_non_nan = np.array(unique_choices)[
            ~np.isnan(unique_choices)
        ]
        unique_choices_n_back = unique_choices_non_nan.__len__()

        if self.block_probability_index is None:
            self.switch_block()

        prob = self.probabilities[self.block_probability_index]

        # stage anti bias
        if self.stage_anti_bias_bool:
            self._check_stage_anti_bias(choice_vector)

        self._check_forced_exploration_trial(
            n_back_crit, prob, unique_choices_n_back, unique_choices_non_nan
        )

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
        sma = self.make_state_machine(
            as_forced_choice_trial=self.is_forced_exploration_trial,
            forced_choice_side=-1 * unique_choices[-1]
            if len(unique_choices)
            else 0,
        )
        logging.debug("New trial drawn")
        return sma

    def _check_forced_exploration_trial(
        self, n_back_crit, prob, unique_choices_n_back, unique_choices_non_nan
    ):
        self.is_forced_exploration_trial = False
        if (
            self.block_trial_number >= n_back_crit
            and unique_choices_n_back == 1
        ):
            try:
                if self.last_choice != (np.argmax(prob) - 1):
                    # only intervene if the choice is suboptimal
                    logging.warning(
                        "NEXT SHOULD BE FORCED TRIAL AS IS SUB-OPTIMAL"
                    )
            except TypeError:
                print("FIX ERROR HERE")

            self.is_forced_exploration_trial = True  # FIXME
            side_dict = {
                -1: "left",
                1: "right",
                np.nan: "NAN",
                float("NaN"): "NAN",
            }
            try:
                logging.warning(
                    f"FORCED EXPLORATION TRIAL NEXT. "
                    f"After {n_back_crit} choices to the {side_dict[unique_choices_non_nan[-1]]}, "
                    f"the next trial enforces a {side_dict[-1 * unique_choices_non_nan[-1]]} choice."
                )
            except KeyError:
                print("HERE AGAIN", n_back_crit, unique_choices_non_nan)
                self.is_forced_exploration_trial = False
                print("ERROR, therefore trying to avoid forced choice now")

    def _check_stage_anti_bias(self, choice_vector):
        # n_back_crit_bias = 3
        bias_unique_choices = np.unique(
            choice_vector[-self.n_back_crit_bias :]
        )
        bias_unique_choices_non_nan = np.array(bias_unique_choices)[
            ~np.isnan(bias_unique_choices)
        ]
        bias_unique_choices_n_back = bias_unique_choices_non_nan.__len__()
        if (
            self.stage_anti_bias_bool
            and bias_unique_choices_n_back == 1
            and self.block_trial_number >= self.n_back_crit_bias
        ):
            # only one type of choice AND only evaluate during current block analog to forced-choice trials
            print("ANTI BIAS")
            if np.abs(self.stage_bias) <= self.stage_bias_max:
                print("BIAS NOT MAXED OUT")
                if self.last_choice == -1:  # LEFT
                    bias_increment = -self.stage.small_increment
                elif self.last_choice == 1:  # RIGHT
                    bias_increment = self.stage.small_increment
                else:
                    print("shouldn't occur!")
                    bias_increment = 0

                self.stage.known_positions["front"]["x"][
                    "position_raw"
                ] += bias_increment

                print(
                    f"NEW ANTI BIAS position: {bias_increment} -> {self.stage.known_positions}"
                )

    def make_state_machine(
        self, as_forced_choice_trial=False, forced_choice_side=-1
    ):
        logging.debug(
            f"Making new StateMachine. Outcomes are "
            f"left={self.next_trial_choice_outcome_left}, "
            f"right={self.next_trial_choice_outcome_right}"
        )

        # LIGHTS - if intensity - for chosen ports (center/side)
        output_actions__center_ready = []
        output_actions__side_ready = []

        # SMA
        sma = StateMachine(bpod=self.bpod)

        # TTL -> center ready
        state_center_ready = "center_ready"
        sma = add_trial_onset_ttl(
            sma=sma,
            ttl_pulse_duration=self.task_settings["ttl_pulse_duration"],
            bnc_channel=eval(
                f"Bpod.OutputChannels.BNC{self.task_settings['HARDWARE_BNC_TRIAL_START']}"
            ),
            next_state=state_center_ready,
        )

        # stage moves forward -> side ready
        state_side_ready = "side_ready"
        sma.add_state(
            state_name=state_center_ready,
            state_timer=0.80,
            state_change_conditions={Bpod.Events.Tup: state_side_ready},
            output_actions=output_actions__center_ready
            + [("SoftCode", self.MOVE_TO_FRONT)],
        )

        if self.task_settings["lick_detection_events"] == "ports":
            state_change_conditions_lick = {
                Bpod.Events.Port1In: "choice_left",
                Bpod.Events.Port3In: "choice_right",
            }
        elif self.task_settings["lick_detection_events"] == "bnc":
            state_change_conditions_lick = {
                Bpod.Events.BNC1Low: "choice_left",
                Bpod.Events.BNC2Low: "choice_right",
            }
        else:
            raise ValueError(f"Unknown option for 'lick_detection_events': "
                             f"{self.task_settings['lick_detection_events']}"
                             )

        state_change_conditions_lick.update({Bpod.Events.Tup: "final"})

        sma.add_state(
            state_name=state_side_ready,
            state_timer=self.task_settings["delay_until_side_timeout"],
            state_change_conditions=state_change_conditions_lick,
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

        # NORMAL TRIAL
        state_change_conditions_left = {Bpod.Events.Tup: outcome_doc_left}
        state_change_conditions_right = {Bpod.Events.Tup: outcome_doc_right}
        state_change_conditions_side_ready = {
            Bpod.Events.Tup: state_side_ready
        }

        # DEBUG
        # as_forced_choice_trial = True
        # forced_choice_side = -1

        # FORCED CHOICE
        if as_forced_choice_trial:
            if forced_choice_side == -1:  # left
                state_change_conditions_right = (
                    state_change_conditions_side_ready
                )
                output_action_right_valve = []
            elif forced_choice_side == 1:  # right
                state_change_conditions_left = (
                    state_change_conditions_side_ready
                )
                output_action_left_valve = []
            else:
                logging.warning(
                    f"\n\n\n\n -> as_forced_choice_trial: {as_forced_choice_trial}, "
                    f"but forced_choice_side: {forced_choice_side} <- \n\n\n\n"
                )

        sma.add_state(
            state_name="choice_left",
            state_timer=valve_left_outcome,
            state_change_conditions=state_change_conditions_left,
            output_actions=output_action_left_valve + [],
        )
        sma.add_state(
            state_name="choice_right",
            state_timer=valve_right_outcome,
            state_change_conditions=state_change_conditions_right,
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
        ITI = self.task_settings.get("inter_trial_interval")
        if isinstance(ITI, int):
            iti_this_trial = ITI
        elif len(ITI) == 3:
            iti_this_trial = draw_jittered_trial_time(*ITI)
            logging.info(f"Drawn ITI for next trial of {iti_this_trial}s.")
        else:
            raise ValueError

        sma.add_state(
            state_name="iti",
            state_timer=iti_this_trial,
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
        save_trial_data(self.trial_data, str(self.save_path_data) + ".df.jsonl")
        logging.debug(f"Saved data in {np.round(time.time()-dt,2)}s.")

    def on_exit(self):
        self.save()

    def __del__(self):
        self.softcode_handler(softcode=self.MOVE_TO_BACK)
        logging.debug("Moved stage BACK on exit")

        self.save()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.softcode_handler(softcode=self.MOVE_TO_BACK)
        logging.debug("Moved stage BACK on exit")

        self.save()
