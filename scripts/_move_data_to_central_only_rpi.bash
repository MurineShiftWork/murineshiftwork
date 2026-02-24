#!/bin/bash

#source ~/murine_shift_work/scripts/collate_acquisition_data.sh

target_path="/mnt/maindata/data/"

#echo "\n\n SETUPS \n\n"#
#
#parallel --line-buffer -j 10 rsync -avh --no-inc-recursive --info=progress2 '{1}:~/data/' $target_path \
#	--exclude=".git" \
#	--exclude="__*" \
#	--exclude=".idea" \
#	--exclude="tests" \
#	--exclude="*.egg-info" \
#	--exclude="default_acq_name" \
#	::: \
#	npxb

#	setup1 setup2 setup3 setup4 setup5 setup6 setup-npxb

#	rpi-40 rpi-41 rpi-43 rpi-50 rpi-51
#       --exclude="_test*" \
#       --exclude="_*" \

echo "\n\n RPI \n\n"

parallel --line-buffer -j 10 rsync -avh --no-inc-recursive --info=progress2 '{1}:~/data/' $target_path \
        --exclude=".git"  \
        --exclude="__pycache__" \
        --exclude=".idea" \
        --exclude="tests" \
        --exclude="*.egg-info" \
	::: \
	rpi-21 rpi-22 rpi-23 rpi-31 rpi-32 rpi-33 rpi-41 rpi-42 rpi-43 rpi-51 rpi-52 rpi-53 rpi-61 rpi-62 rpi-63 rpi-71 rpi-72 rpi-73 rpi-101 rpi-102 rpi-103 rpi-104

#for rpi in rpi-40 rpi-41 rpi-43 rpi-50 rpi-51
#do
#	printf "\n\n \t ${rpi} \n"
#	rsync -av --info=progress2 $rpi':~/data/' $target_path \
#        --exclude=".git" \
#        --exclude="__pycache__" \
#        --exclude=".idea" \
#        --exclude="tests" \
#        --exclude="*.egg-info"
#done

#exit 0
#for rpi in rpi-40 rpi-41 rpi-43 rpi-50 rpi-51
#do
#	: #	ssh $rpi sudo rm -rf "${source_dir}/*"
#done
