#!/bin/bash

NAME="pybpod"
REPO="~/code/pybpod_lbr/"

conda create -n $NAME python=3.8 numpy -y
conda activate $NAME
pip install opencv-python==4.3.0.36  # version was not relevant on macos, but later version seems to break it on 20.04
pip install PyQtWebEngine pybpod sounddevice
cd $REPO
pip install -e .