#!/bin/bash

#source ~/murine_shift_work/scripts/collate_acquisition_data.sh

target_path="/mnt/maindata/data/"

parallel -j 10 rsync -av --info=progress2 '{1}:~/data/' $target_path \
	--exclude=".git" \
	--exclude="__pycache__" \
	--exclude=".idea" \
	--exclude="tests" \
	--exclude="*.egg-info" \
	--exclude="_test*" \
	--exclude="_*" \
	--exclude="default_acq_name" \
	::: \
	setup1 setup2 setup3 setup4 setup5 #\
#	rpi-40 rpi-41 rpi-43 rpi-50 rpi-51

parallel --line-buffer -j 10 rsync -av --info=progress2 '{1}:~/data/' $target_path \
        --exclude=".git"  \
        --exclude="__pycache__" \
        --exclude=".idea" \
        --exclude="tests" \
        --exclude="*.egg-info" \
	::: \
	rpi-40 rpi-41 rpi-43 rpi-50 rpi-51

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
