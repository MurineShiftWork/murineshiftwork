# Serial addresses

|   | Setup | Device      |    | by-path                                | MAC (by-id) | /dev/tty* |
|---|------:|:------------|:---|----------------------------------------|:------------|:----------|
|   |   msw | scale       |    | pci-0000:00:14.0-usb-0:9.4.4:1.0       |             | ACM1      |
|   |       |             |    |                                        |             |           |
| o |     1 | bpod        |    | pci-0000:00:14.0-usb-0:9.1:1.0         |             | ACM2      |
| o |     1 | stage       |    | pci-0000:00:14.0-usb-0:9.2:1.0-port0   |             | USB0      |
|   |     1 | arduino     |    | pci-0000:00:14.0-usb-0:4:1.0           |             | ACM0      |
|   |       |             |    |                                        |             |           |
| o |     2 | bpod        |    | pci-0000:00:14.0-usb-0:9.3.3:1.0       |             | ACM3      |
| o |     2 | stage       |    | pci-0000:00:14.0-usb-0:9.3.1:1.0-port0 |             | USB1      |
|   |       |             |    |                                        |             |           |
| o |     3 | bpod        |    | pci-0000:00:14.0-usb-0:9.4.1:1.0       |             |           |
| o |     3 | stage       |    | pci-0000:00:14.0-usb-0:9.4.2:1.0-port0 |             |           |
|   |       |             |    |                                        |             |           |
| o |     4 | bpod        |    | pci-0000:00:14.0-usb-0:12:1.0          |             |           |
| o |     4 | stage       |    | pci-0000:00:14.0-usb-0:10:1.0-port0    |             |           |
|   |       |             |    |                                        |             |           |
| o |   npx | bpod        |    |                                        |             |           |
| o |   npx | stage       |    |                                        |             |           |
|   |       |             |    |                                        |             |           |
|   |       | bpod 8 port |    | pci-0000:00:14.0-usb-0:1:1.0           |             |           |


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
> Protocol `-t calibrate_water_with_serial_scale`  

```bash

murineshiftwork run -t calibrate_water_with_serial_scale \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:12:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup4.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup4.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup4.yaml \
  -meta x=51 y=52 z=53 \
  -o /mnt/maindata/data/ \
  -scale $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.4.4:1.0)

```

### setup1
```bash

murineshiftwork run -t fixedsubj\
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.1:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.2:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup1.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup1.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup1.yaml \
  -meta x=11 y=12 z=13 \
  -o /mnt/maindata/data/ -s s115_acute_m1102187_120

calibrate_stage
fixedsubj
-s SUBJECTNAME

```

### setup2
```bash

murineshiftwork run -t fixedsubj\
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.3.3:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.3.1:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup2.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup2.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup2.yaml \
  -meta x=41 y=42 z=43 \
  -o /mnt/maindata/data/ -s s118_acute_m1102190_242

calibrate_stage
fixedsubj
-s SUBJECTNAME

```

### setup3
```bash
murineshiftwork run -t fixedsubj\
 -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.4.1:1.0) \
 -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:9.4.2:1.0-port0) \
 -cs /mnt/maindata/CONFIG_FILES/subject.settings \
 -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup3.fixed.from.murinemanager \
 -cwater ~/.murineshiftwork/calibration.water.setup3.csv \
 -cstage ~/.murineshiftwork/calibration.stage.setup3.yaml \
 -meta x=71 y=72 z=73 \
 -o /mnt/maindata/data/ -s s116_acute_m1102188_132

```

### setup4
```bash
murineshiftwork run -t flush\
-b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:12:1.0) \
-stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10:1.0-port0) \
-cs /mnt/maindata/CONFIG_FILES/subject.settings \
-cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup4.fixed.from.murinemanager \
-cwater ~/.murineshiftwork/calibration.water.setup4.csv \
-cstage ~/.murineshiftwork/calibration.stage.setup4.yaml \
-meta x=51 y=52 z=53 \
-o /mnt/maindata/data/ -s s118_acute_m1102190_242


```

