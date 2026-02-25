# Install of RCE on colony

1. ssh-copy-id:`./ssh-copy-id-all.sh`
   2. update .ssh.config with host names, then 
3. step through install to test on one setup
    ```
    ansible-playbook -i inventory.ini deploy.yaml --tags checks --limit setup1 --step
    ```
4. `sudo rpi-update` && `sudo reboot now` for fix of possible FRAMERATES
   5. THIS has its own playbook now under `firmware-updater.sh`
