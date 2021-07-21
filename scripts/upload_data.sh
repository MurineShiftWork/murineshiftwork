#!/bin/sh


find ~/data/behaviour -type f -name "*.pyc" -delete
find ~/data/behaviour -type d -name "__pycache__" -exec rm -rfv {} +

rsync -a \
	--info=progress2 \
	~/data/behaviour \
	larsr@ssh.swc.ucl.ac.uk:/nfs/winstor/sjones/users/lars/ACQUISITION/setup_npx/ \
	--exclude="_test_subject"
