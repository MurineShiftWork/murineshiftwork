#!/bin/sh

source_dir="/home/lbr/data/behaviour"
target_dir="/home/lbr/data"
# project_dir="murine_shift_work"

for setup in setup1router setup2 setup3 setup4 setup5
do
	echo "\n - Loading from $setup : $source_dir -> $target_dir"
	rsync -a --info=progress2 "$setup:$source_dir" $target_dir
done

#rsync -a --info=progress2 "setup1router:$data_dir" $data_dir
#rsync -a --info=progress2 "setup2:$data_dir" $data_dir
#rsync -a --info=progress2 "setup3:$data_dir" $data_dir
#rsync -a --info=progress2 "setup4:$data_dir" $data_dir
#rsync -a --info=progress2 "setup5:$data_dir" $data_dir
#rsync -a --info=progress2 "npxb:$data_dir" $data_dir
