import logging
import random
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine

from murine_shift_work.tasks.probabilistic_switching import task_settings
from murine_shift_work.tools.calibration_handling import get_calibration_point_for_valve
from murine_shift_work.tools.calibration_handling import (
    get_sound_delay_correction_value,
)
from murine_shift_work.tools.maths import ExponentialMovingAverage
from murine_shift_work.tools.maths import withprob
from murine_shift_work.tools.misc import get_session_file_basename
from murine_shift_work.tools.sounds import Sounds
from murine_shift_work.tools.specific_state_machines import add_trial_onset_ttl


class TaskControl(object):
    bpod = None
    sound = None
    sound_delay_correction = 0

    trial_data = []
    save_path_data = None

    # Task progress
    trial_index = 0
    block_number = 0
    block_trial_number = 0
    reward_number = 0

    # Block switches -- length range: 10 - 20+
    min_block_length = 10
    mean_neutral_block_length = 25  # 10 trials difference to min block length
    min_trials_post_criterion = 5
    trials_post_criterion = 0

    criterion_contrast_blocks = 0.6
    criterion_neutral_blocks = 0.2
    criterion_tau = 5
    criterion_block_switch_reached = False
    block_switch_hazard_rate = 1 / (mean_neutral_block_length - min_block_length)

    moving_average = ExponentialMovingAverage(
        tau=criterion_tau, init_value=0.0
    )  # 0=sides coded as -1/1 for left/right, so init value has to be center == 0

    probabilities = task_settings.PROBABILITIES
    block_probability_index = None
    probability_left = 0
    probability_right = 0

    next_trial_choice_outcome_left = 0
    next_trial_choice_outcome_right = 0
    next_trial_give_stop_signal = 0
    stop_signal_delay = None
    stop_trial_success = None

    last_choice = 0
    last_rewarded = 0
    last_punish = 0
    last_stop = 0

    def __init__(self, bpod=None, save_path_data=None):
        super(TaskControl, self).__init__()

        if not bpod:
            raise ValueError("Required input argument: bpod")
        self.bpod = bpod

        self.save_path_data = (
            get_session_file_basename(bpod) if not save_path_data else save_path_data
        )
        print(f"Running session: {Path(self.save_path_data).name}")

        # todo: implement loading of presets for basic PS (no stop)
        #  and stop signal PS (adaptive stops, probabilities all 1/0 for analysis simplicity)

        # fixme: use hardware params for go/stop signal generation
        self.sound = Sounds()

        self.sound_delay_correction = get_sound_delay_correction_value()
        self.valve_times_dict = get_calibration_point_for_valve(
            valves=task_settings.HARDWARE_VALVES_FOR_WATER,
            target_volume=task_settings.REWARD_AMOUNT_UL,
        )

        # copy task_settings to session folder
        src = Path(task_settings.__file__)
        dst = self.save_path_data.parent / src.name
        shutil.copy(src=str(src), dst=str(dst))

        logging.debug("Task control class created.")

    def softcode_handler(self, softcode=None):
        self.sound.soft_code_handler_function(softcode=softcode)

    def switch_block(self):
        logging.debug("Resetting block.")
        self.block_number += 1
        self.block_trial_number = 0
        self.trials_post_criterion = 0
        self.criterion_block_switch_reached = False
        self.moving_average.reset()

        # probabilities
        # if not self.block_probability_index:
        #     self.block_probability_index = 0

        range_for_prob = np.arange(self.probabilities.__len__())
        next_probs_allowed = list(
            set(range_for_prob) - set([self.block_probability_index])
        )
        if len(next_probs_allowed) == 1:
            self.block_probability_index = next_probs_allowed[0]
        else:
            self.block_probability_index = next_probs_allowed[
                random.randint(0, len(next_probs_allowed) - 1)
            ]

        new_prob = self.probabilities[self.block_probability_index]
        self.probability_left, self.probability_right = [x / 100 for x in new_prob]
        # fixme: convert to probability beforehand, not by 100 division

        print(
            f"New block #{self.block_number} after trial #{self.trial_index} with probabilities {self.probability_left}/{self.probability_right}"
        )

        # TODO: block update rules fixed trials vs criterion

    def update(self, trial_index=None, trial_data=None):
        self.trial_index = trial_index
        # trial_data is: bpod start ts, trial start ts, trial end ts, state and event ts

        first_state_name = str(list(trial_data["States timestamps"].keys())[0]).lower()
        if self.trial_index < 1 and first_state_name.startswith(
            "pulse"
        ):  # IF TTL TRIAL
            self.switch_block()
            trial_data["info"] = {"trial_type": "ttl", "trial_index": self.trial_index}
            return self.trial_data.append(trial_data)

        # IF TASK TRIAL
        self.block_trial_number += 1

        st = trial_data["States timestamps"]
        times_left = st["choice_left"][0]
        times_right = st["choice_right"][0]

        outcome_left_reward = (
            st["outcome_left_reward"][0]
            if "outcome_left_reward" in st.keys()
            else [np.nan]
        )
        outcome_right_reward = (
            st["outcome_right_reward"][0]
            if "outcome_right_reward" in st.keys()
            else [np.nan]
        )
        outcome_left_punish = (
            st["outcome_left_punish"][0]
            if "outcome_left_punish" in st.keys()
            else [np.nan]
        )
        outcome_right_punish = (
            st["outcome_right_punish"][0]
            if "outcome_right_punish" in st.keys()
            else [np.nan]
        )

        if not np.isnan(np.array(times_left)).any():
            self.last_choice = -1
        elif not np.isnan(np.array(times_right)).any():
            self.last_choice = 1
        else:
            self.last_choice = np.nan  # timeout / no response

        # Update last choice
        self.moving_average.update(latest_sample=self.last_choice)
        # Update last outcome: reward/neutral/punish
        if (self.next_trial_choice_outcome_left and self.last_choice == -1) or (
            self.next_trial_choice_outcome_right and self.last_choice == 1
        ):
            self.reward_number += 1
            self.last_rewarded = 1
            self.last_punish = 0
        else:
            self.last_rewarded = 0
            if (self.next_trial_choice_outcome_left < 0 and self.last_choice == -1) or (
                self.next_trial_choice_outcome_right < 0 and self.last_choice == 1
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
            "block_type_values": self.probabilities[self.block_probability_index],
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
            f"({round(task_settings.REWARD_AMOUNT_UL*self.reward_number, 2):>4}uL). {item_end}"
            f"Crit: {self.trials_post_criterion:>2}"
        )

        # Check for block criterion
        neutral_block_bias = (
            np.abs(self.moving_average()) <= self.criterion_neutral_blocks
        )

        if self.criterion_block_switch_reached:
            self.trials_post_criterion += 1
        elif self.block_trial_number >= self.min_block_length and (
            (self.probability_left == self.probability_right and neutral_block_bias)
            or (
                self.probability_left > self.probability_right
                and self.moving_average() < -self.criterion_contrast_blocks
            )
            or (
                self.probability_right > self.probability_left
                and self.moving_average() > self.criterion_contrast_blocks
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

    def make_forced_exploration_sma(self, next_choice_option=None):
        if next_choice_option < 0:  # LEFT
            left_valve = task_settings.HARDWARE_VALVES_FOR_WATER[0]
            output_action_only_valve = [(Bpod.OutputChannels.Valve, left_valve)]
            valve_outcome = self.valve_times_dict[left_valve]
            port_nr = left_valve
            side_name = "left"
        else:
            right_valve = task_settings.HARDWARE_VALVES_FOR_WATER[1]
            output_action_only_valve = [(Bpod.OutputChannels.Valve, right_valve)]
            valve_outcome = self.valve_times_dict[right_valve]
            port_nr = right_valve
            side_name = "right"

        output_actions__side_ready = [
            (
                eval(f"Bpod.OutputChannels.PWM{port_nr}"),
                task_settings.HARDWARE_PORT_LIGHT_INTENSITY,
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
            ttl_pulse_duration=task_settings.TTL_PULSE_DURATION,
            bnc_channel=eval(
                f"Bpod.OutputChannels.BNC{task_settings.HARDWARE_BNC_TRIAL_START}"
            ),
            next_state="side_ready",
        )
        # WAITING
        sma.add_state(
            state_name="side_ready",
            state_timer=20,
            state_change_conditions={**state_change_condition, Bpod.Events.Tup: "exit"},
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
            state_timer=task_settings.STATE_DURATION_FINAL,
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
        if self.block_trial_number >= 20:
            key = "choice"
            n_back_crit = 20
            td_info = [td["info"] for td in self.trial_data if td and key in td["info"]]
            choice_vector = [c[key] for c in td_info if key in c.keys()]
            unique_choices = np.unique(choice_vector[-n_back_crit:])
            unique_choices_n_back = unique_choices.__len__()

            if unique_choices_n_back == 1:
                return self.make_forced_exploration_sma(
                    next_choice_option=-1 * unique_choices[-1]
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
        self.next_trial_give_stop_signal = task_settings.USE_STOP_TRIALS and withprob(
            task_settings.STOP_TRIAL_PROPORTION
        )
        if self.next_trial_give_stop_signal:
            # if stop, also punish ?
            self.next_trial_choice_outcome_left = (
                -1
                if task_settings.PUNISH_STOP_TRIALS
                and withprob(task_settings.PUNISH_STOP_TRIALS_PROPORTION)
                else 0
            )
            self.next_trial_choice_outcome_right = (
                -1
                if task_settings.PUNISH_STOP_TRIALS
                and withprob(task_settings.PUNISH_STOP_TRIALS_PROPORTION)
                else 0
            )

            if self.stop_signal_delay is None:
                self.stop_signal_delay = task_settings.STOP_TRIAL_DELAY_INITIAL

            # TODO: STOP signal adaptive testing here: change of stop signal delay ++ self.sound_delay_correction

        # Stimulation
        if task_settings.STIMULATION and withprob(
            task_settings.STIMULATION_TRIAL_PROPORTION
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
        output_actions__center_delay = []
        output_actions__side_ready = []
        if task_settings.HARDWARE_PORT_LIGHT_INTENSITY:
            if "center" in task_settings.HARDWARE_PORT_LIGHT_PORTS:
                output_actions__center_ready = [
                    (
                        Bpod.OutputChannels.PWM2,
                        task_settings.HARDWARE_PORT_LIGHT_INTENSITY,
                    )
                ]
                output_actions__center_delay = output_actions__center_ready
            if "side" in task_settings.HARDWARE_PORT_LIGHT_PORTS:
                output_actions__side_ready = [
                    (
                        Bpod.OutputChannels.PWM1,
                        task_settings.HARDWARE_PORT_LIGHT_INTENSITY,
                    ),
                    (
                        Bpod.OutputChannels.PWM3,
                        task_settings.HARDWARE_PORT_LIGHT_INTENSITY,
                    ),
                ]

        initiation_hold_time = task_settings.DELAY_UNTIL_CENTER_INIT
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
            available_hold_times = np.round(available_hold_times, 3)  # ms rounding
            initiation_hold_time = available_hold_times[
                np.random.randint(0, len(available_hold_times))
            ]
            print(f"-- Drawn new initiation hold time of {initiation_hold_time}s.")

        # SMA
        sma = StateMachine(bpod=self.bpod)

        sma = add_trial_onset_ttl(
            sma=sma,
            ttl_pulse_duration=task_settings.TTL_PULSE_DURATION,
            bnc_channel=eval(
                f"Bpod.OutputChannels.BNC{task_settings.HARDWARE_BNC_TRIAL_START}"
            ),
            next_state="center_ready",
        )

        # TRIAL
        sma.add_state(
            state_name="center_ready",
            state_timer=30,
            state_change_conditions={Bpod.Events.Port2In: "center_initiating"},
            output_actions=output_actions__center_ready,
        )
        # INIT long enough -> proceed. pulled out too early -> back to center_ready
        sma.add_state(
            state_name="center_initiating",
            state_timer=initiation_hold_time,
            state_change_conditions={
                Bpod.Events.Port2Out: "center_ready",  # ABORTED
                Bpod.Events.Tup: "side_ready",
            },  # CONTINUE
            output_actions=output_actions__center_delay,
        )

        # TRAVEL to side -> wait for entry
        if self.next_trial_give_stop_signal:
            delay_until_stop_signal = (
                self.stop_signal_delay - self.sound_delay_correction
            )
            delay_until_side_timeout = (
                task_settings.DELAY_UNTIL_SIDE_TIMEOUT_FOR_STOPPING
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
            #           no entry -> next trial
            #
            # SWITCH signal:
            #       mouse moving
            #       side ready + wait for delay
            #       side ready + trigger sound
            #           side in -> AIR
            #           center light -> center in -> reward

            sma.add_state(
                state_name="side_ready",
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
                    Bpod.Events.Port2In: "exit",
                    Bpod.Events.Port3In: "choice_right",
                    Bpod.Events.Tup: "exit",
                },
                output_actions=output_actions__side_ready
                + [("SoftCode", self.sound.sound_stop_softcode)],
            )
        else:  # REGULAR TRIAL
            sma.add_state(
                state_name="side_ready",
                state_timer=task_settings.DELAY_UNTIL_SIDE_TIMEOUT,
                state_change_conditions={
                    Bpod.Events.Port1In: "choice_left",
                    Bpod.Events.Port3In: "choice_right",
                    Bpod.Events.Tup: "exit",
                },
                output_actions=output_actions__side_ready,
            )

        # OUTCOMES: LEFT  --  Encoding:  0=unrewarded, 1=rewarded, -1=punish with air
        # note: stop signal outcomes set to 0 in next-trial
        if self.next_trial_choice_outcome_left > 0:  # REWARD
            left_valve = task_settings.HARDWARE_VALVES_FOR_WATER[0]
            output_action_left_valve = [(Bpod.OutputChannels.Valve, left_valve)]
            valve_left_outcome = self.valve_times_dict[left_valve]
        elif self.next_trial_choice_outcome_left < 0:  # PUNISH
            output_action_left_valve = [
                (Bpod.OutputChannels.Valve, task_settings.HARDWARE_VALVES_FOR_AIR[0])
            ]
            valve_left_outcome = task_settings.PUNISH_AIR_DURATION_SEC
        else:  # == 0
            output_action_left_valve = []
            valve_left_outcome = 0

        # OUTCOMES: RIGHT  --  Encoding:  0=unrewarded, 1=rewarded, -1=punish with air
        if self.next_trial_choice_outcome_right > 0:  # REWARD
            right_valve = task_settings.HARDWARE_VALVES_FOR_WATER[1]
            output_action_right_valve = [(Bpod.OutputChannels.Valve, right_valve)]
            valve_right_outcome = self.valve_times_dict[right_valve]
        elif self.next_trial_choice_outcome_right < 0:  # PUNISH
            output_action_right_valve = [
                (Bpod.OutputChannels.Valve, task_settings.HARDWARE_VALVES_FOR_AIR[1])
            ]
            valve_right_outcome = task_settings.PUNISH_AIR_DURATION_SEC
        else:  # == 0
            output_action_right_valve = []
            valve_right_outcome = 0

        outcome_codes = {-1: "punish", 0: "neutral", 1: "reward"}
        outcome_doc_left = (
            f"outcome_left_{outcome_codes[self.next_trial_choice_outcome_left]}"
        )
        outcome_doc_right = (
            f"outcome_right_{outcome_codes[self.next_trial_choice_outcome_right]}"
        )

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
            state_timer=0,
            state_change_conditions={Bpod.Events.Tup: "final"},
            output_actions=[],
        )
        sma.add_state(
            state_name=outcome_doc_right,
            state_timer=0,
            state_change_conditions={Bpod.Events.Tup: "final"},
            output_actions=[],
        )
        # Cleanup
        sma.add_state(
            state_name="final",
            state_timer=task_settings.STATE_DURATION_FINAL,
            state_change_conditions={
                Bpod.Events.Port1Out: "exit",
                Bpod.Events.Port2Out: "exit",
                Bpod.Events.Port3Out: "exit",
                Bpod.Events.Tup: "exit",
            },
            output_actions=[],
        )
        # END
        return sma

    def save(self):
        logging.debug("Saving task control data.")
        # TODO: write analysis module to save data preprocessed
        df = pd.DataFrame(self.trial_data)
        df.to_pickle(str(self.save_path_data) + ".pkl")

    def __del__(self):
        self.save()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()
