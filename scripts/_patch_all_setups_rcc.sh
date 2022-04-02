#!/bin/sh
# Script: patch_all_setups_rcc.sh. Update code on list of RPi
git clone https://llrrr@bitbucket.org/lbrcoding/rpi_camera_colony_dev.git ~/rpi_camera_colony_dev
cd ~/rpi_camera_colony_dev/ || exit 1
git pull

for rpi in rpi-40 rpi-41 rpi-43 rpi-50 rpi-51 rpi-70 rpi-60 rpi-61 rpi-62 rpi-63 rpi-64 rpi-65 rpi-67 rpi-68 rpi-69
do
	printf "\n\n\n $rpi \n\n\n"
	
	rsync -av ~/rpi_camera_colony_dev/* $rpi:/home/pi/code/rpi_camera_colony/  \
	  --exclude=".git" \
	  --exclude="__pycache__" \
	  --exclude=".idea" \
	  --exclude="tests" \
	  --exclude="*.egg-info"
	  
	ssh $rpi sudo nohup rm -rf /home/pi/code/rpi_camera_colony/*.egg-info
	  
	#ssh $rpi sudo nohup 'x=$(pip cache dir); rm -rf $x'
	ssh $rpi sudo nohup /home/pi/miniconda3/bin/conda install pandas numpy -y
	ssh $rpi sudo nohup /home/pi/miniconda3/bin/conda install -n py36 pandas numpy -y
	ssh $rpi sudo nohup /home/pi/miniconda3/envs/py36/bin/pip install -e /home/pi/code/rpi_camera_colony
done
