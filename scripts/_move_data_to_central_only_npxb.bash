#!/bin/bash

target_path="/mnt/maindata/data/"

echo "\n\n SETUPS \n\n"

parallel --line-buffer -j 10 rsync -av --info=progress2 '{1}:~/data/' $target_path \
	--exclude=".git" \
	--exclude="__*" \
	--exclude=".idea" \
	--exclude="tests" \
	--exclude="*.egg-info" \
	--exclude="default_acq_name" \
	::: \
	murinemanager npxb

printf "\n DONE \n\n"
