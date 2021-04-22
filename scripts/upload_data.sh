#!/bin/sh

# 1) mkdir /mnt/winstor
# 2) mkdir /home/$USER/credentials
# 3) nano /home/$USER/credentials/$USER

username="lbr"
credentials_file="/home/$username/credentials/$username"
upload_dir="/mnt/winstor/sjones/users/lars/ACQUISITION/setups_pybpod/"
mount_point="/mnt/winstor"

sudo mount -t cifs -o credentials=$credentials_file,nodfs,uid=$(id -u),gid=$(id -g),_netdev,x-systemd.device-timeout=4,nofail //winstor.id.swc.ucl.ac.uk/winstor/swc $mount_point
ls -lah $upload_dir

rsync -a --info=progress2 "/home/$username/code/pybpod_lbr/main_project" $upload_dir

sudo umount -f $mount_point
ls -lah $mount_point
