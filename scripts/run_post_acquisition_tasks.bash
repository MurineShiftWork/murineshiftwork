#!/bin/bash

eval script_path="~/code/murineshiftwork/scripts"

rsync -a --info=progress2 ~/data/ /mnt/maindata/data/

bash  $script_path/_move_data_to_central_only_rpi.bash
bash  $script_path/_convert_h264_to_mp4.bash
bash  $script_path/_clean_msw_files.bash

bash  $script_path/upload_data.sh
# printf "\n\n -->> Manually UPLOAD acquisition data with $script_path/upload_data.sh \n\n"

printf "\n\n -->> Manually REMOVE acquisition data with $script_path/_remove_all_data.sh \n\n"
