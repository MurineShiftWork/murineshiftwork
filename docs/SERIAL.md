# Serial addresses

| Setup | Device | by-path                                                                         | MAC (by-id)                                                            | /dev/tty* |
|------:|:-------|---------------------------------------------------------------------------------|:-----------------------------------------------------------------------|:----------|
|     1 | bpod   | pci-0000:00:14.0-usb-0:2:1.0   pci-0000:00:14.0-usb-0:4.4:1.0                   | usb-Teensyduino_USB_Serial_5817740-if00                                | ACM1      |
|     1 | stage  | pci-0000:00:14.0-usb-0:1:1.0-port0   pci-0000:00:14.0-usb-0:4.3:1.0-port0       | usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_0001-if00-port0 | USB0      |
|       |        |                                                                                 |                                                                        |           |
|     2 | bpod   | pci-0000:00:14.0-usb-0:4.1.4:1.0                                                | usb-Teensyduino_USB_Serial_9289480-if00                                | ACM0      |
|     2 | stage  | pci-0000:00:14.0-usb-0:4.2:1.0-port0                                            |                                                                        | USB1      |
|       |        |                                                                                 |                                                                        |           |
|     3 | bpod   | pci-0000:00:14.0-usb-0:4.1.2:1.0                                                | usb-Teensyduino_USB_Serial_5789440-if00                                | ACM2      |
|     3 | stage  | pci-0000:00:14.0-usb-0:4.1.3:1.0-port0                                          |                                                                        | USB2      |
|       |        |                                                                                 |                                                                        |           |
|     4 | bpod   | pci-0000:00:14.0-usb-0:4.1.1:1.0                                                | usb-Teensyduino_USB_Serial_5816670-if00                                | ACM3      |
|     4 | stage  | pci-0000:00:14.0-usb-0:10.2:1.0-port0                                           |                                                                        | USB3      |
|       |        |                                                                                 |                                                                        |           |
|     5 | bpod   | pci-0000:00:14.0-usb-0:10.1.3:1.0     pci-0000:00:14.0-usb-0:10.1.3:1.0         | usb-Teensyduino_USB_Serial_5818020-if00                                | ACM5      |
|     5 | stage  | pci-0000:00:14.0-usb-0:10.4:1.0-port0   pci-0000:00:14.0-usb-0:10.1.4:1.0-port0 |                                                                        | USB4      |
|       |        |                                                                                 |                                                                        |           |
|     6 | bpod   | pci-0000:00:14.0-usb-0:10.1.2:1.0                                               | usb-Teensyduino_USB_Serial_5817240-if00                                | ACM4      |
|     6 | stage  | pci-0000:00:14.0-usb-0:10.1.1:1.0-port0                                         |                                                                        | USB5      |


setup1
```shell

murineshiftwork run -t flush \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:2:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup1.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup1.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup1.yaml \
  -meta x=21 y=22 z=23


murineshiftwork run -t calibrate_stage \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:2:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup1.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup1.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup1.yaml \
  -meta x=21 y=22 z=23


murineshiftwork run -t fixedsubj \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:2:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup1.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup1.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup1.yaml \
  -meta x=21 y=22 z=23 \
  -s s071_tabfixedctrl_m1099155_No

```

setup2
```shell

murineshiftwork run -t flush \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.1.4:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.2:1.0-port0)  \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup2.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup2.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup2.yaml \
  -meta x=11 y=12 z=13


murineshiftwork run -t calibrate_stage \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.1.4:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.2:1.0-port0)  \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup2.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup2.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup2.yaml \
  -meta x=11 y=12 z=13


murineshiftwork run -t fixedsubj \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.1.4:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.2:1.0-port0)  \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup2.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup2.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup2.yaml \
  -meta x=11 y=12 z=13


```

setup3
```shell

murineshiftwork run -t flush \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.1.2:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.1.3:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup3.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup3.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup3.yaml \
  -meta x=41 y=42 z=43


murineshiftwork run -t calibrate_stage \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.1.2:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.1.3:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup3.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup3.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup3.yaml \
  -meta x=41 y=42 z=43


murineshiftwork run -t fixedsubject \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.1.2:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.1.3:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup3.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup3.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup3.yaml \
  -meta x=41 y=42 z=43 \
  -s s073_tabfixedctrl_m1099157_R \
  -d



```

setup4
```shell

murineshiftwork run -t flush \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.1.1:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10.2:1.0-port0)  \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup4.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup4.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup4.yaml \
  -meta x=51 y=52 z=53


murineshiftwork run -t calibrate_stage \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.1.1:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10.2:1.0-port0)  \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup4.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup4.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup4.yaml \
  -meta x=51 y=52 z=53


murineshiftwork run -t fixedsubject \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:4.1.1:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10.2:1.0-port0)  \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup4.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup4.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup4.yaml \
  -meta x=51 y=52 z=53 \
  -s s074_tabfixedctrl_m1099158_LR


```

setup5
```shell

murineshiftwork run -t flush \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10.1.3:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10.4:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup5.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup5.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup5.yaml \
  -meta x=71 y=72 z=73


murineshiftwork run -t calibrate_stage \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10.1.3:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10.4:1.0-port0) \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup5.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup5.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup5.yaml \
  -meta x=71 y=72 z=73

```

setup6
```shell

murineshiftwork run -t calibrate_stage \
  -b $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10.1.2:1.0) \
  -stage $(realpath /dev/serial/by-path/pci-0000:00:14.0-usb-0:10.1.1:1.0-port0)  \
  -cs /mnt/maindata/CONFIG_FILES/subject.settings \
  -cc /mnt/maindata/CONFIG_FILES/camera.rcc.setup6.fixed.from.murinemanager \
  -cwater ~/.murineshiftwork/calibration.water.setup6.csv \
  -cstage ~/.murineshiftwork/calibration.stage.setup6.yaml \
  -meta x=61 y=62 z=63

```



```shell
lrwxrwxrwx 1 root root  13 Nov  3 16:09 pci-0000:00:14.0-usb-0:11.1.1:1.0-port0 -> ../../ttyUSB3
lrwxrwxrwx 1 root root  13 Nov  3 16:52 pci-0000:00:14.0-usb-0:4.1.2:1.0 -> ../../ttyACM0
lrwxrwxrwx 1 root root  13 Nov  3 16:52 pci-0000:00:14.0-usb-0:4.1.3:1.0-port0 -> ../../ttyUSB2
lrwxrwxrwx 1 root root  13 Nov  3 16:52 pci-0000:00:14.0-usb-0:4.1.4:1.0 -> ../../ttyACM2
lrwxrwxrwx 1 root root  13 Nov  3 16:52 pci-0000:00:14.0-usb-0:4.2:1.0-port0 -> ../../ttyUSB0
lrwxrwxrwx 1 root root  13 Nov  3 16:52 pci-0000:00:14.0-usb-0:4.3:1.0-port0 -> ../../ttyUSB1
lrwxrwxrwx 1 root root  13 Nov  3 16:52 pci-0000:00:14.0-usb-0:4.4:1.0 -> ../../ttyACM1


```

```shell
lrwxrwxrwx 1 root root  13 Nov  3 16:54 pci-0000:00:14.0-usb-0:11.1.1:1.0-port0 -> ../../ttyUSB3
lrwxrwxrwx 1 root root  13 Nov  3 16:54 pci-0000:00:14.0-usb-0:4.1.2:1.0 -> ../../ttyACM0
lrwxrwxrwx 1 root root  13 Nov  3 16:54 pci-0000:00:14.0-usb-0:4.1.3:1.0-port0 -> ../../ttyUSB2
lrwxrwxrwx 1 root root  13 Nov  3 16:54 pci-0000:00:14.0-usb-0:4.1.4:1.0 -> ../../ttyACM2
lrwxrwxrwx 1 root root  13 Nov  3 16:54 pci-0000:00:14.0-usb-0:4.2:1.0-port0 -> ../../ttyUSB0
lrwxrwxrwx 1 root root  13 Nov  3 16:54 pci-0000:00:14.0-usb-0:4.3:1.0-port0 -> ../../ttyUSB1
lrwxrwxrwx 1 root root  13 Nov  3 16:54 pci-0000:00:14.0-usb-0:4.4:1.0 -> ../../ttyACM1

```
