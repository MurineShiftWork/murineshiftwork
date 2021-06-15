#!/bin/sh

data_dir="/home/lbr/data/"
project_dir="murine_shift_work"

rsync -a --info=progress2 "setup1router:/home/lbr/code/${project_dir}/main_project" $data_dir
rsync -a --info=progress2 "setup2:/home/lbr/code/${project_dir}/main_project" $data_dir
rsync -a --info=progress2 "setup3:/home/lbr/code/${project_dir}/main_project" $data_dir
rsync -a --info=progress2 "setup4:/home/lbr/code/${project_dir}/main_project" $data_dir
rsync -a --info=progress2 "setup5:/home/lr/code/${project_dir}/main_project" $data_dir
rsync -a --info=progress2 "npxb:/home/lbr/code/${project_dir}/main_project" $data_dir
