#!/bin/bash

eval script_folder="~/murine_shift_work/scripts"

bash $script_folder/_patch_all_setups_config_files.bash
bash $script_folder/_patch_all_setups_msw.sh
bash $script_folder/_patch_all_setups_rcc.sh
