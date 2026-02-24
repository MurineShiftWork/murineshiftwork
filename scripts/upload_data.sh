#!/bin/sh

data_path="/mnt/maindata/data/"
target_path="/ceph/sjones/users/lars/data/"

# remove unnecessary files .pyc and folders pycache
printf "\n Removing pyc/pycache... \n\n"

find $data_path/ -type f -name "*.pyc" -delete
find $data_path/ -type d -name "__pycache__" -exec rm -rfv {} +

# COPY
printf "\n Files < 50M \n\n"

rsync -amvh --no-inc-recursive $1 --max-size=50M --info=progress2 $data_path/* $target_path/ \
	--exclude="*___test__*" \
	--exclude="*.csv.bak*" \
	--exclude="__pycache__" \
	--exclude="*.pyc*"

printf "\n Files > 50M \n\n"

rsync -amvh --no-inc-recursive $1 --min-size=50M --info=progress2 $data_path/* $target_path/ \
        --exclude="*___test__*" \
        --exclude="*.csv.bak*" \
        --exclude="__pycache__" \
        --exclude="*.pyc*"


rsync -amvh --no-inc-recursive $1 --info=progress2 $data_path/* $target_path/ \
	--exclude="*___test__*" \
	--exclude="*.csv.bak*" \
	--exclude="__pycache__" \
	--exclude="*.pyc*"

printf "\n DONE \n\n"
