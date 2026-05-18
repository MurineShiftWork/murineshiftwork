- !! Only setups 1-4 work. I need to upgrade the ephys setup later, so can't train there today.
- I left subject config files open for all task stages (100/0, 90/10, ...) on the right side in PyCharm - as examples to copy in case any mice need to move to next stage today.
- No need to touch the `flush` or any other files anymore; check out the new commands below!

---
FLUSH
---

murineshiftwork run --setup setup-1 --task flush_water -ts VALVE_NUMBERS=[1,3] VALVE_OPENING_TIME_MS=40000


---
MOVE STAGE == CALIBRATE STAGE
---

murineshiftwork run --setup setup-1 --task stage_move


---
TASK
---

murineshiftwork run --setup setup-1 --task probabilistic_switching_fixedsubjects --subject t022_acute_m1102629_220
