# Install of RCE on colony

1. ssh-copy-id:`./ssh-copy-id-all.sh`
   2. update .ssh.config with host names, then 
3. step through install to test on one setup
    ```
    ansible-playbook -i inventory.ini deploy.yaml --tags checks --limit setup1 --step
    ```
4. `sudo rpi-update` && `sudo reboot now` for fix of possible FRAMERATES
   5. THIS has its own playbook now under `firmware-updater.sh`

## Issues

### Web UI init acquisition gets stuck on same UUID, when not shut down properly

### TTL-out ok, but TTL-in not written properly
format is: (timestamp, ttl level) rows.
NPZ extension, but written as CSV !

```
head t004_acute_m1102390_177__20260226_135958__probabilistic_switching_fixedsubjects.rce.rpi-142.20260226135959.ttl_in.npz

timestamp,data
1772114405.9972267,1
1772114406.002559,0
1772114406.1026044,1
1772114406.107473,0
1772114406.2073162,1
1772114406.2124505,0
1772114406.3123267,1
1772114406.317419,0
1772114406.5171561,1
```
while TTL-out is correct numpy npz file with fields:
```
sensor_ts, monotonic_ts
```
