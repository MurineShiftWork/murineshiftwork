#!/bin/sh

data_path="/mnt/maindata/data/"
#target_path="larsr@ssh.swc.ucl.ac.uk:/nfs/winstor/sjones/users/lars/ACQUISITION/behaviour/"
target_path="/mnt/winstor/sjones/users/lars/ACQUISITION/behaviour/"

# remove unnecessary files .pyc and folders pycache
find ~/data/ -type f -name "*.pyc" -delete
find ~/data/ -type d -name "__pycache__" -exec rm -rfv {} +

rsync -av $1 --info=progress2 $data_path/* $target_path/ \
	--exclude="_test_subject" \
	--exclude="default_acq_*" \
	--exclude="*___test__*" \
	--exclude="*.csv.bak.2*" \
	--exclude="_*"

printf "\nDONE\n"
