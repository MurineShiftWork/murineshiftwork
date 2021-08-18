#!/bin/sh

# remove unnecessary files .pyc and folders pycache
find ~/data/ -type f -name "*.pyc" -delete
find ~/data/ -type d -name "__pycache__" -exec rm -rfv {} +

# exclude test_subject from upload
# exclude unnamed acquisitions from video source
# exclude test protocols like _test_flush_water
# exclude old "main_project" folder
rsync -av $1 --info=progress2 ~/data/* larsr@ssh.swc.ucl.ac.uk:/nfs/winstor/sjones/users/lars/ACQUISITION/behaviour/ --exclude="_test_subject" --exclude="default_acq_*" --exclude="*___test__*" --exclude="*.csv.bak.2*"
