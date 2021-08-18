#!/bin/sh
# Script: patch_msw_and_rcc.sh. Update MSW and RCC code on main setups.
# Run as: cat patch_msw_and_rcc.sh | ssh setup2

git clone https://llrrr@bitbucket.org/lbrcoding/rpi_camera_colony_dev.git ~/rpi_camera_colony_dev
git clone https://llrrr@bitbucket.org/lbrcoding/murine_shift_work.git ~/murine_shift_work
cd ~/murine_shift_work
git pull
cd ~

~/miniconda3/envs/acq/bin/pip uninstall murine_shift_work -yq
~/.conda/envs/acq/bin/pip uninstall murine_shift_work -yq

~/miniconda3/envs/acq/bin/pip install -e ~/murine_shift_work -q
~/.conda/envs/acq/bin/pip install -e ~/murine_shift_work -q

