#!/bin/bash

eval script_path="~/murine_shift_work/scripts"

bash $script_path/patch_all_setups_msw.sh
bash $script_path/patch_all_setups_rcc.sh

bash  $script_path/_mv_all_data.bash
bash  $script_path/_clean_msw_files.sh
bash  $script_path/_convert_h264_to_mp4.sh

bash  $script_path/upload_data.sh

printf "\n\n -->> Manually remove acquisition data with $script_path/_remove_all_data.sh \n\n"
