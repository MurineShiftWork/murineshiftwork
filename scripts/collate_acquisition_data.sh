#!/bin/bash

eval source_dir="~/data/behaviour"
eval target_dir="~/data"

# Collate data from all setups
for setup in setup1router setup2 setup3 setup4 setup5 # npxb
do
	echo "\n - Loading from $setup : $source_dir -> $target_dir"
	rsync -a --info=progress2 \
		"$setup:$source_dir" \
		$target_dir \
		--exclude="_test_subject*" \
		--exclude="*_test__*" \
		--exclude="*.pyc" \
		--exclude="*__pycache__*"

done

# echo "Removing remote files.."
# Do NOT remove files from setup 1 - these will be uploaded!
ssh setup2 rm -rf "${source_dir}/*/*"
ssh setup3 rm -rf "${source_dir}/*/*"
ssh setup4 rm -rf "${source_dir}/*/*"
ssh setup5 rm -rf "${source_dir}/*/*"
#ssh npxb rm -rf "${source_dir}/*/*"

# find $target_dir -type f -name "*.pyc" -delete
# find $target_dir -type d -name "__pycache__" -exec rm -rfv {} +

echo "Removing noise events 'Port4'..."
ts=$(date +%Y%m%d_%H%M%S)

find $target_dir -name "*.csv" -print0 | while read -d $'\0' file
do
	echo $file

	if stat -t "${file}."* >/dev/null 2>&1
	then
		echo "" # Already exists. Do nothing.
	else
		echo "Cleaning file: ${file}"
		sed "-i.bak.${ts}" '/Port4/d' $file
	fi

done

# Alternative for cleaning files without checking if file exists:
# find $target_dir -type f -name "*.csv" -exec sed "-i.bak.${ts}" '/Port4/d' {} +

#
