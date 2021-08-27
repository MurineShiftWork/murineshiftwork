#!/bin/sh
# Script: patch_all_setups_rcc.sh. Update code on list of RPi
git clone https://llrrr@bitbucket.org/lbrcoding/rpi_camera_colony_dev.git ~/rpi_camera_colony_dev
cd ~/rpi_camera_colony_dev/ || exit 1
git pull

for rpi in rpi-40 rpi-41 rpi-43 rpi-50 rpi-51
do
	echo "\n\n\n $rpi"
	rsync -av ~/rpi_camera_colony_dev/* $rpi:/home/pi/code/rpi_camera_colony/  \
	  --exclude=".git" \
	  --exclude="__pycache__" \
	  --exclude=".idea" \
	  --exclude="tests" \
	  --exclude="*.egg-info"
	ssh $rpi sudo nohup /home/pi/miniconda3/envs/py36/bin/pip install -e /home/pi/code/rpi_camera_colony[rpi]
done
