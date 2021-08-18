#!/bin/bash

#source ~/murine_shift_work/scripts/collate_acquisition_data.sh

source_dir="/home/pi/data"
parallel -j 8 rsync -av "{1}:$source_dir/" ~/data/ --exclude=".git" --exclude="__pycache__" --exclude=".idea" --exclude="tests" --exclude="*.egg-info" ::: rpi-40 rpi-41 rpi-43 rpi-50 rpi-51

for rpi in rpi-40 rpi-41 rpi-43 rpi-50 rpi-51
do
	ssh $rpi sudo rm -rf "${source_dir}/*"
done
