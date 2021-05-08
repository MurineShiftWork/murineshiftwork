#!/bin/sh

data_dir="/home/lbr/data/"

rsync -a --info=progress2 setup1router:/home/lbr/code/pybpod_lbr/main_project $data_dir
rsync -a --info=progress2 setup2:/home/lbr/code/pybpod_lbr/main_project $data_dir
rsync -a --info=progress2 setup3:/home/lbr/code/pybpod_lbr/main_project $data_dir
rsync -a --info=progress2 setup4:/home/lbr/code/pybpod_lbr/main_project $data_dir
rsync -a --info=progress2 setup5:/home/lr/code/pybpod_lbr/main_project $data_dir
