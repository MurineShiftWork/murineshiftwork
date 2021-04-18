#!/bin/bash

# https://sites.google.com/site/bpoddocumentation/installing-bpod/ubuntu14
sudo apt-get install linux-lowlatency

#https://stackoverflow.com/questions/49333582/portaudio-library-not-found-by-sounddevice
sudo apt-get install libportaudio2

#https://stackoverflow.com/questions/60042568/this-application-failed-to-start-because-no-qt-platform-plugin-could-be-initiali
sudo apt-get install qt5-default

# https://askubuntu.com/questions/359856/share-wireless-internet-connection-through-ethernet

# Add line to /etc/fstab
#//winstor.id.swc.ucl.ac.uk/winstor/swc/ /mnt/winstor    cifs    credentials=/home/lbr/credentials/swc_larsr,_netdev,vers=3.0,uid=1000,gid=1000  0       0
# create file /home/lbr/credentials/swc_larsr with content: username=XXX, password=XXX
