ipi_8hz = round(1 / 8 / 2, 3)
ipi_10hz = round(1 / 10 / 2, 3)
ipi_14hz = round(1 / 14 / 2, 3)


def calc_pulse_train_duration(n_pulses=4, interval=None, spacer=0.5):
    return round(n_pulses * 2 * interval - spacer * interval, 3)


stimulation_param_sets = {
    # 0: {
    #     "phase1Duration": ipi_8hz,
    #     "interPulseInterval": ipi_8hz,
    #     "pulseTrainDuration": calc_pulse_train_duration(n_pulses=4, interval=ipi_8hz),
    # },
    # 1: {
    #     "phase1Duration": ipi_10hz,
    #     "interPulseInterval": ipi_10hz,
    #     "pulseTrainDuration": calc_pulse_train_duration(n_pulses=4, interval=ipi_10hz),
    # },
    0: {
        "phase1Duration": ipi_8hz,
        "interPulseInterval": ipi_8hz,
        "pulseTrainDuration": calc_pulse_train_duration(
            n_pulses=10, interval=ipi_8hz
        ),
    },
    1: {
        "phase1Duration": ipi_10hz,
        "interPulseInterval": ipi_10hz,
        "pulseTrainDuration": calc_pulse_train_duration(
            n_pulses=10, interval=ipi_10hz
        ),
    },
    # 4: {
    #     "phase1Duration": ipi_14hz,
    #     "interPulseInterval": ipi_14hz,
    #     "pulseTrainDuration": calc_pulse_train_duration(n_pulses=10, interval=ipi_14hz),
    # },
}

# 4 pulses at 8Hz
# 4 pulses at 10Hz
# 10 pulses at 8Hz
# 10 pulses at 14 Hz

# GENERAL
# - ITI > 10sec
# - random interleave
# - No-stim periods: 5min ON, 5min OFF
