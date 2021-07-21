#!/bin/sh


find ~/data/ -type f -name "*.pyc" -delete
find ~/data/ -type d -name "__pycache__" -exec rm -rfv {} +

rsync -a \
	--info=progress2 \
	~/data/* \
	larsr@ssh.swc.ucl.ac.uk:/nfs/winstor/sjones/users/lars/ACQUISITION/setup_npx/ \
	--exclude="_test_subject" \	# remove test_subject from upload
	--exclude="default_acq_name*"	# remove unnamed acquisitions from video source
	--exclude="*_test__*"		# remvoe test protocols like _test__flush_water
