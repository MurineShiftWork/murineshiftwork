## todo for ephys/behavior setups to run last cohort of GPe mice

tests for behavior setups
- [x] serial port addresses for bpod/stages
- [x] rpi addresses match positions on setups + update
- [x] add two rpi + cams for setups 5/6
  - [ ] add last camera onto setup 5 + add both new cameras into rcc config files
- [x] soy milk use + cleaning

setups
- [ ] add digital TTL output to spout firmware, so that getting a move/no-move signal into the ephys system
- [ ] fix spout python firmware. there is some infinite recursion in there somewhere
- [ ] decide on synch TTL hardware and wire it up with original NPX setup
- [ ] camera synch: fix dropout of synch TTL for both ephys setup AND behavior setups that rely on this to use video!!
- [x] decide on camera positions: front/sides/mirror

analysis
- [ ] fix SSD storage bottleneck for database, ie for tagging and regression

surgeries
- [ ] do target test and slice
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
