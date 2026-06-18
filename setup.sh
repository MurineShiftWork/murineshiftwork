#!/bin/bash
# Dependencies
# https://sites.google.com/site/bpoddocumentation/installing-bpod/ubuntu14
# https://stackoverflow.com/questions/49333582/portaudio-library-not-found-by-sounddevice
# https://stackoverflow.com/questions/60042568/this-application-failed-to-start-because-no-qt-platform-plugin-could-be-initiali
# https://askubuntu.com/questions/359856/share-wireless-internet-connection-through-ethernet

sudo apt-get install linux-lowlatency libportaudio2 qt5-default --upgrade -y
# ! now requires:
conda update libstdcxx-ng
conda update libgcc-ng
