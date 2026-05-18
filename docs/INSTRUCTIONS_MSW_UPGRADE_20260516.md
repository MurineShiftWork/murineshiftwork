
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

---
Look up subject name
---
msw subject list --filter "t0"

---
Move subject to next task level
---
murineshiftwork run --setup setup-1 --task probabilistic_switching_fixedsubjects --task-mode stage30prob905010

stage00habituation
stage10deterministic
stage20prob9010
stage30prob905010


murineshiftwork run --setup setup-npx2 --task flush_water -ts VALVE_NUMBERS=[2,1,6,3,7] VALVE_OPENING_TIME_MS=2000 FLUSH_VALVES_SEQUENTIALLY=true


murineshiftwork run --setup setup-npx2 --task _calibration_liquid_dynamic -ts VALVES_TO_CALIBRATE=[1,2,3,4,5,6,7,8] TARGET_RANGE_UL=[1.0,10.0]
