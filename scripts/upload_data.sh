#!/bin/sh

data_path="/mnt/maindata/data/"
#target_path="larsr@ssh.swc.ucl.ac.uk:/nfs/winstor/sjones/users/lars/ACQUISITION/data/"
target_path="/mnt/ceph/users/lars/data/"

# remove unnecessary files .pyc and folders pycache
find $data_path/ -type f -name "*.pyc" -delete
find $data_path/ -type d -name "__pycache__" -exec rm -rfv {} +

rsync -amvh --no-inc-recursive $1 --max-size=10M --info=progress2 $data_path/* $target_path/ \
	--exclude="*___test__*" \
	--exclude="*.csv.bak*" \
	--exclude="__pycache__" \
	--exclude="*.pyc*"
#       --exclude="_*" \

rsync -amvh --no-inc-recursive $1 --info=progress2 $data_path/* $target_path/ \
	--exclude="*___test__*" \
	--exclude="*.csv.bak*" \
	--exclude="__pycache__" \
	--exclude="*.pyc*"

printf "\n DONE \n\n"
