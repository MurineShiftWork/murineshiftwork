# Serial addresses

## Known issues: Bpod firmware and USB reliability

### Bpod firmware version vs pybpod-api

pybpod-api has a hard-coded `MAX_FIRMWARE_VERSION` constant in `bpod_base.py`.
If the Bpod firmware version number exceeds this cap, the handshake fails with:
`Error: Future firmware detected. Please update the Bpod python software.`

**Verified working combination:** firmware v22, machine type r0.5, pybpod-api 1.8.2.

Three version numbers interact independently:
| Version | What it is | Where to check |
|---|---|---|
| Hardware revision | PCB generation (r0.5, r0.9, r1.0) | Printed on the board |
| Firmware version | Protocol number reported at connect | Shown in `bpod_connect` output |
| State machine version | State machine protocol (usually matches firmware) | Shown in `bpod_connect` output |

r0.5 hardware → firmware v22 (pybpod-api 1.8.2 compatible).
r0.9 / r1.0 hardware → needs firmware compiled for r0.9/r1.0; if the firmware version
number exceeds pybpod-api's cap, either use the older firmware build or bump
`MAX_FIRMWARE_VERSION` in the installed `bpod_base.py`.

### 8-port Bpod mid-session disconnects after firmware reflash

Symptom: boards connect successfully (firmware version accepted by pybpod-api)
but fail mid-session with `Error: The last state machine sent was not acknowledged`.

**Root cause:** firmware-hardware revision mismatch. If the wrong firmware variant
is flashed (e.g. r0.5 build onto r0.9 silicon), the initial handshake may pass
because the version byte is within pybpodapi's accepted range, but timing constants,
port interrupt handlers, or valve channel mappings differ between revisions and
cause state machine failures after a few trials.

**Diagnosis:**
1. Connect one working board via Arduino IDE and note exact firmware version + machine type.
2. Connect a failing board the same way: compare. If versions differ, reflash to match.
3. If versions already match, the firmware binary used for reflashing may have been
   built for a different hardware revision. Source the correct binary from the
   Bpod firmware repository and reflash.

**Key rule:** always match the firmware binary to the hardware revision printed on the PCB.
Do not assume "latest firmware" works on all revisions: r0.5, r0.9, and r1.0 each
have distinct binaries. The working reference is firmware v22 on r0.5 hardware with
pybpod-api 1.8.2.

MSW retries the connection 5 times with 2 s delays (`factory.py`). This handles
brief USB settle issues but cannot recover from a sustained power or bandwidth problem.

|   | Setup | Device      |    | by-path                                   | MAC (by-id) | /dev/tty* |
|---|------:|:------------|:---|-------------------------------------------|:------------|:----------|
|   |   msw | scale       |    | pci-0000:00:14.0-usb-0:9.4.4:1.0          |             | ACM1      |
|   |  npxb | scale       |    | pci-0000:00:14.0-usbv2-0:10.4.2:1.0       |             | ACM1      |
|   |       |             |    |                                           |             |           |
| o |     1 | bpod        |    | pci-0000:00:14.0-usb-0:9.1:1.0            |             | ACM2      |
| o |     1 | stage       |    | pci-0000:00:14.0-usb-0:9.2:1.0-port0      |             | USB0      |
|   |     1 | arduino     |    | pci-0000:00:14.0-usb-0:4:1.0              |             | ACM0      |
|   |       |             |    |                                           |             |           |
| o |     2 | bpod        |    | pci-0000:00:14.0-usb-0:9.3.3:1.0          |             | ACM3      |
| o |     2 | stage       |    | pci-0000:00:14.0-usb-0:9.3.1:1.0-port0    |             | USB1      |
|   |       |             |    |                                           |             |           |
| o |     3 | bpod        |    | pci-0000:00:14.0-usb-0:9.4.1:1.0          |             |           |
| o |     3 | stage       |    | pci-0000:00:14.0-usb-0:9.4.2:1.0-port0    |             |           |
|   |       |             |    |                                           |             |           |
| o |     4 | bpod        |    | pci-0000:00:14.0-usb-0:9.3.4:1.0          |             |           |
| o |     4 | stage       |    | pci-0000:00:14.0-usb-0:9.4.3:1.0-port0    |             |           |
|   |       |             |    |                                           |             |           |
| o |   npx | bpod        |    | pci-0000:00:14.0-usb-0:10.1:1.0           |             |           |
| o |   npx | stage       |    | pci-0000:00:14.0-usb-0:10.4.4.3:1.0-port0 |             |           |
| o |   npx | pulsepal    |    | pci-0000:00:14.0-usb-0:10.2:1.0           |             |           |
|   |       |             |    |                                           |             |           |
|   |       | bpod 8 port |    | pci-0000:00:14.0-usb-0:1:1.0              |             |           |


| Setup | Stage id | x  | y  | z  | cam btm | cam L | cam R | cam front |
|-------|----------|----|----|----|---------|-------|-------|-----------|
| 1     | 1        | 11 | 12 | 13 | 21      | 22    | 23    | 101       |
| 2     | 2        | 41 | 42 | 43 | 102     | 32    | 33    | 31        |
| 3     | 3        | 71 | 72 | 73 | 42      | 43    | 41    | 103       |
| 4     | 4        | 51 | 52 | 53 | 61      | 53    | 52    | 51        |
| -     | 5        | 61 | 62 | 63 | -       | -     | -     | -         |
| -     | 6        | 21 | 22 | 23 | -       | -     | -     | -         |
| npx   | 7        | 31 | 32 | 33 | 73      | 71    | 72    | 104       |


### Water calibration example for setup 4

> Add `-scale` parameter with serial device path
> Protocol `-t _calibration_water_with_serial_scale`

```bash

murineshiftwork run -t _calibration_water_with_serial_scale \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:12:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc ~/.murineshiftwork/setup4-rce.yaml \
  -cwater ~/.murineshiftwork/calibration.water.setup4.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup4.yaml \
  -meta x=51 y=52 z=53 \
  -o /mnt/maindata/data/ \
  -scale $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.4.4:1.0)

```


### setup NPXB
```bash

murineshiftwork run -t flush \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10.1:1.0) \
  -p $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10.2:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10.4.4.3:1.0-port0) \
  -cs /mnt/fastdata/CONFIG_FILES/subject.settings \
  -cc ~/.murineshiftwork/setup-npxb-rce.yaml \
  -cwater ~/.murineshiftwork/calibration.water.setup.npxb.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup.npxb.yaml \
  -meta x=31 y=32 z=33 setup=npxb \
  -o /mnt/fastdata/data/ -s s115_acute_m1102187_120

calibrate_stage
fixedsubj
-s SUBJECTNAME

```


### setup1
```bash

murineshiftwork run -t fixedsubj \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.1:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.2:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc ~/.murineshiftwork/setup1-rce.yaml \
  -cwater ~/.murineshiftwork/calibration.water.setup1.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup1.yaml \
  -meta x=11 y=12 z=13 setup=setup1\
  -o /mnt/maindata/data/ -s s115_acute_m1102187_120

calibrate_stage
fixedsubj
-s SUBJECTNAME

```

### setup2
```bash

murineshiftwork run -t fixedsubj \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.3.3:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.3.1:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc ~/.murineshiftwork/setup2-rce.yaml \
  -cwater ~/.murineshiftwork/calibration.water.setup2.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup2.yaml \
  -meta x=41 y=42 z=43 setup=setup2\
  -o /mnt/maindata/data/ -s s118_acute_m1102190_242

calibrate_stage
fixedsubj
-s SUBJECTNAME

```

### setup3
```bash
murineshiftwork run -t fixedsubj \
 -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.4.1:1.0) \
 -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.4.2:1.0-port0) \
 -cs /mnt/maindata/CONFIG_FILES/subject.settings \
 -cc ~/.murineshiftwork/setup3-rce.yaml \
 -cwater ~/.murineshiftwork/calibration.water.setup3.csv \
 -cstage ~/.murineshiftwork/calibration.stage.setup3.yaml \
 -meta x=71 y=72 z=73 setup=setup3\
 -o /mnt/maindata/data/ -s s116_acute_m1102188_132

```

### setup4
```bash
murineshiftwork run -t flush \
-b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.3.4:1.0) \
-stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.4.3:1.0-port0) \
-cs /mnt/maindata/CONFIG_FILES/subject.settings \
-cc ~/.murineshiftwork/setup4-rce.yaml \
-cwater ~/.murineshiftwork/calibration.water.setup4.csv \
-cstage ~/.murineshiftwork/calibration.stage.setup4.yaml \
-meta x=51 y=52 z=53 setup=setup4 \
-o /mnt/maindata/data/ -s s118_acute_m1102190_242


```
