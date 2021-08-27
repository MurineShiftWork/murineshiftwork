#!/bin/bash

fps=60

find ~/data/ -type f -name "*.h264" -print0 |
    while IFS= read -r -d '' file; do
	converted_file=${file}.mp4

	if stat -t $converted_file >/dev/null 2>&1
	then
		:	# converted_file exists
	else
		printf "\n ==>> Converting file: $f"
		MP4Box -fps $fps -add $file $converted_file
	fi
    done
