#!/bin/sh
# Script: patch_rcc_on_rpi.sh. Update code on list of RPi

for rpi in rpi-40 rpi-41 rpi-43 rpi-50 rpi-51
do
	echo "\n\n\n $rpi"
	rsync -av ~/rpi_camera_colony_dev/* $rpi:/home/pi/code/rpi_camera_colony/  --exclude=".git" --exclude="__pycache__" --exclude=".idea" --exclude="tests" --exclude="*.egg-info"
	ssh $rpi sudo nohup /home/pi/miniconda3/envs/py36/bin/pip install -e /home/pi/code/rpi_camera_colony[rpi]
done
