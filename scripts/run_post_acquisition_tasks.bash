#!/bin/bash

eval script_path="~/murine_shift_work/scripts"

bash  $script_path/_move_data_to_central.bash
bash  $script_path/_convert_h264_to_mp4.bash
bash  $script_path/_clean_msw_files.bash

bash  $script_path/upload_data.sh
# printf "\n\n -->> Manually UPLOAD acquisition data with $script_path/upload_data.sh \n\n" 

printf "\n\n -->> Manually REMOVE acquisition data with $script_path/_remove_all_data.sh \n\n"
