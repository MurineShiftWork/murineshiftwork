#!/bin/bash

source_dir="/mnt/maindata/CONFIG_FILES"

for setup in setup1 setup2 setup3 setup4 setup5
do
	echo =================  $setup
	rsync -av $source_dir $setup:'~/'
done

for setup in setup2 setup3 setup4 setup5
do
	echo =================  $setup
	rsync -av ~/.ssh/config $setup:~/.ssh/
done
