# Provision-RPI Scripts — Status and Operations

## Current situation (2026-05-21)

The crontab and `scripts/run_post_acquisition_tasks.sh` both reference shell scripts
at `external/provision_rpi/scripts/` that **do not exist**.

| Expected path | Status |
|---|---|
| `external/provision_rpi/scripts/collate_data2.sh` | **MISSING** |
| `external/provision_rpi/scripts/upload_to_server.sh` | **MISSING** |
| `external/provision_rpi/scripts/h264_to_mp4.sh` | **MISSING** |

The `external/provision_rpi/` directory contains the Python `rpi_camera_ensemble`
package (camera conductor), not shell scripts. The old scripts were in the
BitBucket repo `BAK_bitbucket_rpi_camera_colony/scripts/` under different names:

| Old BAK name | New expected name | Purpose |
|---|---|---|
| `collect_data_from_remotes.sh` | `collate_data2.sh` | rsync RPi → central |
| `upload_data.sh` | `upload_to_server.sh` | rsync central → ceph |
| `convert_h264_to_mp4.sh` | `h264_to_mp4.sh` | video conversion |
| `remove_remote_data.sh` | *(no new name)* | clear RPi storage |

---

## Fix required

Create `external/provision_rpi/scripts/` and either:
- Copy and rename scripts from `BAK_bitbucket_rpi_camera_colony/scripts/`
- Or rewrite them to match the interface expected by `run_post_acquisition_tasks.sh`

Expected interface (from `run_post_acquisition_tasks.sh`):

```bash
# collate_data2.sh: positional $1 = ansible group, $2 = --target-dir=PATH
bash collate_data2.sh rpis --target-dir=/mnt/maindata/data [--dry-run]

# upload_to_server.sh:
bash upload_to_server.sh --source-dir=PATH --target-dir=PATH [--dry-run]

# h264_to_mp4.sh:
bash h264_to_mp4.sh --source-dir=PATH [--dry-run]
```

---

## Fix the crontab

Current broken entry (runs at 01:05 AM daily):

```
5 1 * * * flock -n /tmp/murine_upload.lock bash -c 'mkdir -p /home/murinemanager/log && /mnt/maindata/code/murineshiftwork/external/provision_rpi/scripts/collate_data2.sh >> /home/murinemanager/log/collate_data2.log 2>&1 && /mnt/maindata/code/murineshiftwork/external/provision_rpi/scripts/upload_to_server.sh >> /home/murinemanager/log/upload_to_server.log 2>&1'
```

Replace with (once scripts exist at that path):

```
5 1 * * * flock -n /tmp/murine_upload.lock bash /mnt/maindata/code/murineshiftwork/scripts/run_post_acquisition_tasks.sh --central-data=/mnt/maindata/data --provision-scripts=/mnt/maindata/code/murineshiftwork/external/provision_rpi/scripts >> /home/murinemanager/log/post_acq.log 2>&1
```

---

## How to run operations manually (now)

### Collate data from RPis (rsync RPi cameras → central)

Until scripts are restored, run the underlying ansible/rsync commands directly.
The BAK script uses ansible to rsync each RPi's `~/data/` to the central store:

```bash
# From BAK script — adapt group and target as needed
ansible rpis -m shell -a \
    "rsync -av ~/data/ murinemanager@controller:/mnt/maindata/data/ && echo done" \
    --become-user=pi

# Or per-host if ansible not configured:
rsync -av pi@rpiXX:~/data/ /mnt/maindata/data/
```

### Upload to remote server (central → ceph)

```bash
rsync -avz --progress \
    /mnt/maindata/data/ \
    lars@ceph.cluster:/ceph/sjones/users/lars/data/
```

### Clear RPi storage (remove_remote_data)

Run this only after verifying data has successfully synced to central.
Based on provisioning inventory at `~/.murineshiftwork/msw_machine.yaml` or ansible inventory.

```bash
# From BAK script — clear ~/data/ on each RPi after confirming sync
ansible rpis -m shell -a "rm -rf ~/data/*" --become-user=pi

# Or per-host manually:
ssh pi@rpiXX "rm -rf ~/data/*"
```

**Warning**: only run clear-rpis after confirming rsync completed successfully.

### Convert h264 → mp4

```bash
find /mnt/maindata/data -name "*.h264" | while read f; do
    mp4="${f%.h264}.mp4"
    ffmpeg -framerate 30 -i "$f" -c copy "$mp4" && rm "$f"
done
```

---

## MSW post CLI (skip-only option until scripts are restored)

`msw post run` requires `--provision-scripts` to exist. Run with `--skip-rpi --skip-upload`
to still benefit from the rsync local→central and msw-clean steps:

```bash
msw post run \
    --central-data /mnt/maindata/data \
    --provision-scripts /mnt/maindata/code/murineshiftwork/external/provision_rpi/scripts \
    --skip-rpi \
    --skip-upload \
    --skip-h264
```
