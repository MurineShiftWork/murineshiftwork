#!/bin/sh

for setup in setup1 setup2 setup3 setup4 setup5
do
	printf "\n $setup \n"
	ssh $setup 'rm -rf ~/data/*'
done

for rpi in rpi-40 rpi-41 rpi-43 rpi-50 rpi-51
do
	printf "\n $rpi \n"
	ssh $rpi sudo 'rm -rf ~/data/*'
done
