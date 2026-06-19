# Cameras

MSW records video through a pluggable camera backend declared per setup under
the `cameras:` block. Two backends ship:

- **`rce`** - Raspberry Pi camera ensemble (freely moving rigs): one or more
  networked RPis each running an RCE agent, coordinated by a conductor. Provided
  by [`rpi-camera-ensemble`](https://github.com/MurineShiftWork/rpi-camera-ensemble).
- **`flir_bonsai`** - FLIR/Spinnaker cameras driven by Bonsai subprocesses
  (head-fixed rigs, Windows acquisition machines). Provided by
  [`msw-flir-bonsai`](https://github.com/MurineShiftWork/msw-flir-bonsai).

`cameras: null` (the default) means no cameras are configured and the task runs
without video.

The full key reference for both backends lives in
[Setup Config → Camera config](setup_config.md#camera-config). This page is the
orientation and per-backend bring-up checklist.

## Choosing a backend

| | `rce` | `flir_bonsai` |
|---|---|---|
| Typical rig | Freely moving | Head-fixed |
| Hardware | Networked RPis + ribbon cameras | FLIR/Spinnaker cameras on the acquisition PC |
| Sync | TTL barcodes per agent | TTL barcodes; per-camera serial sidecar |
| Driver | RCE agent + conductor | Bonsai workflow subprocess per camera |

## RCE bring-up (freely moving)

1. Flash each RPi and install the RCE agent package; bring each Pi onto the rig
   network with a known, reserved address (see [DHCP](DHCP.md)).
2. Author the ensemble YAML describing each agent (host, camera id, role) and
   place it under `msw_configs/device_configs/cameras/`.
3. Point the setup at it:
   ```yaml
   cameras:
     backend: rce
     config: device_configs/cameras/<setup>.cameras.yaml
   ```
   `config` is absolute or relative to `msw_configs/`.
4. Verify GPIO in/out, the agent, and the conductor on each Pi before a session.

> Record the physical mapping (camera position ↔ camera id ↔ Pi ↔ network
> address) for **your** rigs in your lab's private config repo, not here - it is
> deployment-specific and not part of the published package.

## FLIR + Bonsai bring-up (head-fixed)

1. Install Bonsai and the Spinnaker/FlyCapture SDK on the acquisition PC.
2. Resolve the Bonsai executable: `msw flir find-bonsai` (or set the `BONSAI_EXE`
   environment variable).
3. List cameras to resolve enumeration indices: `msw flir list-cameras`.
4. Configure the setup:
   ```yaml
   cameras:
     backend: flir_bonsai
     bonsai_exe: C:\Users\<user>\AppData\Local\Bonsai\Bonsai.exe
     cameras:
       - index: 0
   ```
   One Bonsai subprocess is launched per camera entry. Per-camera optical
   parameters (gain, shutter, exposure) are set inside the Bonsai workflow XML,
   not in this config.
5. Smoke-test: `msw flir test-record`, then run a task with the backend set.

Enumeration `index` is not guaranteed stable across reboots; the per-camera
serial is recorded in the FLIR session sidecar
(see [Setup Config → FLIR session metadata sidecar](setup_config.md#flir-session-metadata-sidecar)).

## Synchronisation

Both backends rely on TTL barcodes for offline alignment of video against Bpod
and ephys: the same 37-bit timestamp pulse train is distributed to each camera
backend so frames can be matched to behavioural and electrophysiology streams
after acquisition.
