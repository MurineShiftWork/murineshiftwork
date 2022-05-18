#!/bin/sh

data_path="/mnt/maindata/data/"
#target_path="larsr@ssh.swc.ucl.ac.uk:/nfs/winstor/sjones/users/lars/ACQUISITION/data/"
target_path="/mnt/winstor/sjones/users/lars/data/"

# remove unnecessary files .pyc and folders pycache
find $data_path/ -type f -name "*.pyc" -delete
find $data_path/ -type d -name "__pycache__" -exec rm -rfv {} +

rsync -amv $1 --info=progress2 $data_path/* $target_path/ \
	--exclude="*___test__*" \
	--exclude="*.csv.bak*" \
	--exclude="__pycache__" \
	--exclude="*.pyc*"
#       --exclude="_*" \

printf "\n DONE \n\n"
