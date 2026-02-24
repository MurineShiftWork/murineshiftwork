# Cameras on head-fixed setups

## Setup

1. Latest OS (bookworm/trixie), user `pi`, pw `piadmin`
2. `gpiod`
3. RCE
   4. venv & package install
   5. RCE agent service
6. Test recording


## Mapping
- Left/right from mouse perspective
- camera position <> camera color <> rpi color < != > rpi hardware order on mount brackets
- pink==purple in the poor light on the setups, so used interchangeably as only one of the two per setup


| Setup | rpi/position | rpi/color  | rpi/mac           | rpi/ip | camera/color | camera/position | OS | GPIO | Py | RCE | Agent |
|-------|--------------|------------|-------------------|--------|--------------|-----------------|----|------|----|-----|-------|
| 1     | 4            | red/yellow | dc:a6:32:34:b1:0d | 111    | red          | top             |    |      |    |     |       |
|       | 3            | orange     | dc:a6:32:d1:28:11 | 112    | orange/white | left            |    |      |    |     |       |
|       | 2            | pink       | dc:a6:32:45:e4:5f | 113    | pink         | right           |    |      |    |     |       |
|       | 1            | green      | dc:a6:32:a2:0f:16 | 114    | green/white  | bottom          |    |      |    |     |       |
| --    |              |            |                   |        |              |                 |    |      |    |     |       |
| 2     | 2            | red        |                   | 121    | red          | top             |    |      |    |     |       |   
|       | 3            | green      |                   | 122    | green        | left            |    |      |    |     |       |
|       | 4            | orange     |                   | 122    | orange       | right           |    |      |    |     |       |
|       | 1            | blue       |                   | 123    | blue         | bottom          |    |      |    |     |       |
| --    |              |            |                   |        |              |                 |    |      |    |     |       |
| 3     | 1            | green      |                   | 131    | green        | top             |    |      |    |     |       |
|       | 4            | yellow     |                   | 132    | yellow       | left            |    |      |    |     |       |
|       | 2            | pink       |                   | 133    | pink         | right           |    |      |    |     |       |
|       | 3            | red        |                   | 134    | red          | bottom          |    |      |    |     |       |
| --    |              |            |                   |        |              |                 |    |      |    |     |       |
| 4     | 3            | red        |                   | 141    | red          | top             |    |      |    |     |       |
|       | 2            | green      |                   | 142    | green        | left            |    |      |    |     |       |
|       | 4            | pink       |                   | 143    | pink         | right           |    |      |    |     |       |
|       | 1            | yellow     |                   | 144    | yellow       | bottom          |    |      |    |     |       |
| --    |              |            |                   |        |              |                 |    |      |    |     |       |
| npxb  | 4            | red        |                   | 171    | red          | top             |    |      |    |     |       |
|       | 3            | yellow     |                   | 172    | yellow       | left            |    |      |    |     |       |
|       | 2            | white      |                   | 173    | white        | right           |    |      |    |     |       |
|       | 1            | pink       |                   | 174    | pink         | bottom          |    |      |    |     |       |
| --    |              |            |                   |        |              |                 |    |      |    |     |       |


## Etc
- https://pinout.xyz/ -> use GPIO labels, not BCM in python for pigpio
