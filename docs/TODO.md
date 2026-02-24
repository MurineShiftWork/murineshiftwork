
# todo for ephys/behavior setups to run last cohort of GPe mice

---

- [ ] reinstall `murinemanager`
- [x] move DHCP to separate machine
- [x] setup 3, 4 calibrations
- [ ] npx calibrations


### Tasks x Setup

| Setup task                         | 1 | 2 | 3 | 4 | npx-HF | npx-Left | npx-Right |
|------------------------------------|---|---|---|---|--------|:---------|:----------|
| HARDWARE                           |   |   |   |   |        |          |           |
|                                    |   |   |   |   |        |          |           |
| Stage firmware                     | x | x | x | x | x      |          |           |
| Install stage repo                 | x | x | x | x |        |          |           |
| Stage config + limits              | x | x |   |   |        |          |           |
| Stage cabling / movable ?          |   |   |   |   |        |          |           |
| Lick circuit (soldering)           |   |   |   |   |        |          |           |
| Serial port loc (bpod/stage)       |   |   |   |   |        |          |           |
| Camera config                      | x | x |   |   |        |          |           |
| Change tubing on all setups        |   |   |   |   |        |          |           |
| Valce/spout electrical connections |   |   |   |   |        |          |           |
| Valve loc for easy cleaning ?      |   |   |   |   |        |          |           |
| IR light reflection ?              |   |   |   |   |        |          |           |
| Trigger: bpod->cam ?               |   |   |   |   |        |          |           |
| Ephys airpuff valve/pressue        |   |   |   |   |        |          |           |
| Ephys trigger: laser, cam, bpod    | - | - | - | - |        |          |           |
|                                    |   |   |   |   |        |          |           |
| SOFTWARE                           |   |   |   |   |        |          |           |
|                                    |   |   |   |   |        |          |           |
| Manipulator atlas tracker          | - | - | - | - |        |          |           |
| MSW-client upgrade                 |   |   |   |   |        |          |           |
| msw-acq-flir: bonsai + ws          | - | - | - | - | -      |          |           |
|                                    |   |   |   |   |        |          |           |
|                                    |   |   |   |   |        |          |           |


### Setup x Stage x Motor ID

| Setup  | Stage ID | x  | y  | z  |                            |
|--------|----------|----|----|----|----------------------------|
| 1      | 1        | 11 | 12 | 13 |                            |
| 2      | 2        | 41 | 42 | 43 |                            |
| 3      | 3        | 71 | 72 | 73 |                            |
| 4      | 4        | 51 | 52 | 53 |                            |
| npx-HF | 7        | 31 | 32 | 33 |                            |
|        |          |    |    |    |                            |
|        | 5        | 61 | 62 | 63 | 62 stuck on baud 1000000 ? |
|        | 6        | 21 | 22 | 23 |                            |


---

tests for behavior setups
- [x] serial port addresses for bpod/stages
- [x] rpi addresses match positions on setups + update
- [x] add two rpi + cams for setups 5/6
  - [x] add last camera onto setup 5 + add both new cameras into rcc config files
- [x] soy milk use + cleaning

test stage
- arduino: pci-0000:00:14.0-usb-0:1:1.0 
- usb controller: pci-0000:00:14.0-usb-0:4:1.0-port0

stage API
- scan: scan all: none -> return: list of devices and info like in 'scan one'
- get: scan one: device id -> return: info of device id, positions raw/degree, op_mode
- set: set property: id, mode, position raw/degree, velocity max
- flash: flash LED: id, n(flashes) -> flashes

command,arg=val,arg2=val2 -> return: success(bool),specifics per command


setups
- [x] add digital TTL output to spout firmware, so that getting a move/no-move signal into the ephys system
- [x] fix spout python firmware. there is some infinite recursion in there somewhere
- [x] decide on synch TTL hardware and wire it up with original NPX setup
- [x] camera synch: fix dropout of synch TTL for both ephys setup AND behavior setups that rely on this to use video!!
- [x] decide on camera positions: front/sides/mirror

analysis
- [x] fix SSD storage bottleneck for database, ie for tagging and regression

surgeries
- [x] do target test and slice
- [ ] figure out way to align probe with bregma more systematically, mark bregma on cement ?
  - implant fibers, ground screw, cover perimeter with cement
  - cut hole for grid, fix in place
  - level bregma/lambda
  - cover with cement
  - mark bregma/lambda on top + note offset from original position
  - ! test approach by then using pipette/probe to level and insert multiple times at same depth in AP sequence, then slice/check
  -
  - ! how can lambda stay clear with the fibers ?

notes for soy milk
- use 50ml tube, fill 40ml, add one spoon of powder
- shake
- fill into setup tubes -> fill each up enough for pressure through tubing
- for 7 setups with two tubes each that take 20ml, but 15ml should be enough, 7x2x15=210ml
- cleaning: empty each tube upside down. refill with water, then use cleaning protocol for valves 20x2sec, use plunger to push all soy out
-
