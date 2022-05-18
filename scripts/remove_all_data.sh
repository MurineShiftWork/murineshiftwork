#!/bin/sh

for setup in setup1 setup2 setup3 setup4 setup5 setup6 setup-npxb
do
	printf "\n $setup \n"
	ssh $setup 'rm -rf ~/data/*'
done

for rpi in rpi-40 rpi-41 rpi-43 rpi-50 rpi-51 rpi-60 rpi-61 rpi-62 rpi-63 rpi-64 rpi-65 rpi-67 rpi-68 rpi-69 rpi-70
do
	printf "\n $rpi \n"
	ssh $rpi sudo 'rm -rf ~/data/*'
done
