#!/bin/sh

#for setup in setup1 setup2 setup3 setup4 setup5 setup6 npxb
#do
#	printf "\n $setup \n"
#	ssh $setup 'rm -rf ~/data/*'
#done

for rpi in rpi-21 rpi-22 rpi-23 rpi-31 rpi-32 rpi-33 rpi-41 rpi-42 rpi-43 rpi-51 rpi-52 rpi-53 rpi-61 rpi-62 rpi-63 rpi-71 rpi-72 rpi-73 rpi-101 rpi-102 rpi-103 rpi-104
do
	printf "\n $rpi \n"
	ssh $rpi sudo 'rm -rf ~/data/*'
done


for setup in murinemanager npxb intan
do
	printf "\n $setup \n"
	ssh $setup 'rm -rf ~/data/*'
done
