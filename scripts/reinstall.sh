#!/usr/bin/env sh

conda activate btest
pip uninstall murine_shift_work -y
pip install -e /home/lbr/code/murine_shift_work[dev]
