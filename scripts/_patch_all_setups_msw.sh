#!/bin/sh
# Script: patch_all_setups_msw.sh. Update MSW and RCC code on main setups.
# Run as: cat patch_all_setups_msw.sh | ssh setup2

for setup in setup1router setup2 setup3 setup4 setup5
do
  ssh $setup << EOF
# Clone
git clone https://llrrr@bitbucket.org/lbrcoding/murine_shift_work.git ~/murine_shift_work

# Update
cd ~/murine_shift_work || exit 1
git reset --hard
git pull

# Un/Reinstall: -y=yes, -q=quiet
if stat -t ~/miniconda3/envs/acq/bin/pip >/dev/null 2>&1
then
  ~/miniconda3/envs/acq/bin/pip uninstall murine_shift_work rpi_camera_colony -yq
  ~/miniconda3/envs/acq/bin/pip install -e ~/murine_shift_work -q
else
  ~/.conda/envs/acq/bin/pip uninstall murine_shift_work rpi_camera_colony -yq
  ~/.conda/envs/acq/bin/pip install -e ~/murine_shift_work -q
fi
EOF
done
