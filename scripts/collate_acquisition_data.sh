#!/bin/sh

source_dir="/home/lbr/data/behaviour"
target_dir="/home/lbr/data"
# project_dir="murine_shift_work"


# exclude protocols that contain test like _test__flush_water
# exclude test_subject sessions without removing them locally

for setup in setup1router setup2 setup3 setup4 setup5
do
	echo "\n - Loading from $setup : $source_dir -> $target_dir"
	rsync -a --info=progress2 \
		"$setup:$source_dir" \
		$target_dir \
		--exclude="_test_subject*" \
		--exclude="*_test__*"
done

find $source_dir -type f -name "*.pyc" -delete
find $target_dir -type d -name "__pycache__" -exec rm -rfv {} +

#rsync -a --info=progress2 "setup1router:$data_dir" $data_dir
#rsync -a --info=progress2 "setup2:$data_dir" $data_dir
#rsync -a --info=progress2 "setup3:$data_dir" $data_dir
#rsync -a --info=progress2 "setup4:$data_dir" $data_dir
#rsync -a --info=progress2 "setup5:$data_dir" $data_dir
#rsync -a --info=progress2 "npxb:$data_dir" $data_dir
