#!/bin/sh

# remove unnecessary files .pyc and folders pycache
find ~/data/ -type f -name "*.pyc" -delete
find ~/data/ -type d -name "__pycache__" -exec rm -rfv {} +

# exclude test_subject from upload
# exclude unnamed acquisitions from video source
# exclude test protocols like _test__flush_water
# exclude old "main_project" folder
rsync -a --info=progress2 ~/data/* larsr@ssh.swc.ucl.ac.uk:/nfs/winstor/sjones/users/lars/ACQUISITION/setup_npx/ --exclude="_test_subject" --exclude="default_acq_name*" --exclude="*___test__*" --exclude="main_project"
