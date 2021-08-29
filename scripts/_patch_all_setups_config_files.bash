#!/bin/bash

for setup in setup1 setup2 setup3 setup4 setup5
do
	echo $setup
	rsync -av ~/murine_shift_work/tests/CONFIG_FILES $setup:~/
done

for setup in setup2 setup3 setup4 setup5
do
	echo $setup
	rsync -av ~/.ssh/config $setup:~/.ssh/
done
