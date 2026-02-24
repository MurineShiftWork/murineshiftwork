#!/bin/sh

data_path="/mnt/maindata/data/"
target_path="/ceph/sjones/users/lars/data/"
nproc=10

find "$data_path" -type f -size -50M \
    ! -path "*___test__*" \
    ! -name "*.csv.bak*" \
    ! -path "*/__pycache__/*" \
    ! -name "*.pyc*" |
sed "s|^$data_path/||" |
parallel -j$(nproc) rsync -amvh --no-inc-recursive $1 --info=progress2 --relative "$data_path"/{} "$target_path/"


# small files
find "$data_path" -type f -size -50M \
    ! -path "*___test__*" \
    ! -name "*.csv.bak*" \
    ! -path "*/__pycache__/*" \
    ! -name "*.pyc*" |
parallel -j$(nproc) rsync -R -amvh --no-inc-recursive $1 --info=progress2 --relative {} "$target_path/"


printf "\n DONE \n\n"
