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

> Two setups are weird and don't have the same packages available as the other ones. rpi-142, rpi-174 ?

| Setup | rpi/position | rpi/color  | rpi/mac           | rpi/ip | camera/color | camera/position | OS | deploy | test: GPIO in | test: GPIO out | test: Agent | test: Conductor |
|-------|--------------|------------|-------------------|--------|--------------|-----------------|----|--------|---------------|----------------|-------------|-----------------|
| 1     | 4            | red/yellow | dc:a6:32:34:b1:0d | 111    | red          | top             | x  | x      | x             | -              | x           | x               |
|       | 3            | orange     | dc:a6:32:d1:28:11 | 112    | orange/white | left            | x  | x      | TODO: oscillo | -              | x           | x               |
|       | 2            | pink       | dc:a6:32:45:e4:5f | 113    | pink         | right           | x  | x      |               | -              | x           | x               |
|       | 1            | green      | dc:a6:32:a2:0f:16 | 114    | green/white  | bottom          | x  | x      |               | -              | x           | x               |
| --    |              |            |                   |        |              |                 |    |        |               |                |             |                 |
| 2     | 2            | red        | dc:a6:32:a9:61:aa | 121    | red          | top             | x  | x      |               | -              | x           | x               |
|       | 3            | green      | dc:a6:32:45:a8:89 | 122    | green        | left            | x  | x      |               | -              | x           | x               |
|       | 4            | orange     | e4:5f:01:1f:d7:10 | 123    | orange       | right           | x  | x      |               | -              | x           | x               |
|       | 1            | blue       | dc:a6:32:34:ae:79 | 124    | blue         | bottom          | x  | x      |               | -              | x           | x               |
| --    |              |            |                   |        |              |                 |    |        |               |                |             |                 |
| 3     | 1            | green      | dc:a6:32:45:a7:e1 | 131    | green        | top             | x  | x      |               | -              | x           | x               |
|       | 4            | yellow     | e4:5f:01:1f:cc:a2 | 132    | yellow       | left            | x  | x      |               | -              | x           | x               |
|       | 2            | pink       | e4:5f:01:1f:d7:4c | 133    | pink         | right           | x  | x      |               | -              | x           | x               |
|       | 3            | red        | dc:a6:32:a9:61:d1 | 134    | red          | bottom          | x  | x      |               | -              | x           | x               |
| --    |              |            |                   |        |              |                 |    |        |               |                |             |                 |
| 4     | 3            | red        | e4:5f:01:1f:d7:45 | 141    | red          | top             | x  | x      |               | -              | x           | x               |
|       | 2            | green      | dc:a6:32:f5:3f:cc | 142    | green        | left            | x  | x      |               | -              | x           | x               |
|       | 4            | pink       | dc:a6:32:d1:27:b4 | 143    | pink         | right           | x  | x      |               | -              | x           | x               |
|       | 1            | yellow     | dc:a6:32:45:e4:92 | 144    | yellow       | bottom          | x  | x      |               | -              | x           | x               |
| --    |              |            |                   |        |              |                 |    |        |               |                |             |                 |
| npxb  | 4            | red        |                   | 171    | red          | top             | x  | x      |               | TODO: with NPX | x           | x               |
|       | 3            | yellow     |                   | 172    | yellow       | left            | x  | x      |               |                | x           | x               |
|       | 2            | white      |                   | 173    | white        | right           | x  | x      |               |                | x           | x               |
|       | 1            | pink       |                   | 174    | pink         | bottom          | x  | x      |               |                | x           | x               |
| --    |              |            |                   |        |              |                 |    |        |               |                |             |                 |


## Etc
- https://pinout.xyz/ -> use GPIO labels, not BCM in python for pigpio
