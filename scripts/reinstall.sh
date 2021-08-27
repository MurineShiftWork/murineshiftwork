#!/usr/bin/env sh

conda activate acq
pip uninstall murine_shift_work -y
pip install -e ~/murine_shift_work[dev]
