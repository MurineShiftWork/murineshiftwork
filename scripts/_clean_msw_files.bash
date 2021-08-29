#!/bin/bash

echo "Removing noise events 'Port4' from MSW files..."

ts=$(date +%Y%m%d_%H%M%S)
eval target_dir="~/data"

counter_all=0
counter_mod=0

find $target_dir -name "*.msw.csv" -print0 | while read -d $'\0' file
do
	counter=$((counter+1))

	if stat -t "${file}."* >/dev/null 2>&1
	then
		:  # Output already exists. Do nothing.
	else
		echo "Cleaning file: ${file}"
		sed "-i.bak.${ts}" '/Port4/d' $file
		counter_mod=$((counter_mod+1))
	fi
done

echo "Looked at $counter_all files and modified $counter_mod of these."
