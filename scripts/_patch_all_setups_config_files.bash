#!/bin/bash

source_dir="/mnt/maindata/CONFIG_FILES"

for setup in setup1 setup2 setup3 setup4 setup5 setup6 npxb
do
	echo =================  $setup
	rsync -av $source_dir $setup:'~/'
done

for setup in setup1 setup2 setup3 setup4 setup5 setup6 npxb
do
	echo =================  $setup
	rsync -av ~/.ssh/config $setup:~/.ssh/
done
