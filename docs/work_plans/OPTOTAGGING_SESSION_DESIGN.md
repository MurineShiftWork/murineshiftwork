# Optotagging Session Design

Reference for the standard optotagging session structure used with the `optotagging` task
(`gpe_somatic` / `gpe_antidromic` task modes). Total session ~9 min.

---

## TODO

- **Per-channel protocol config**: rework stimulation protocol config to be channel-explicit.
  Current flat params apply uniformly to all output channels. Desired hierarchy:

  ```yaml
  stimulation:
    protocol_name:
      channels_ttl_copy: [3]       # optional TTL copy, stays at protocol level
      channels:
        0:                         # PulsePal output ch0 → laser
          pulse_duration: 0.005
          pulse_frequency: 10
          pulse_train_duration: 20.0
          laser_power: 0.108
        1:                         # PulsePal output ch1 → second fiber / control site
          pulse_duration: 0.005
          pulse_frequency: 10
          pulse_train_duration: 20.0
          laser_power: 0.056
  ```

  This allows e.g. simultaneous somatic + antidromic stimulation with different powers per
  fiber in a single protocol, without hacking two Stimulation objects.
  Requires refactor of `logic/stimulation.py` and `Stimulation.__init__`.

---

## Session structure

```
OPTOTAGGING SESSION  (~9 min total)
│
├── SOMATIC BLOCK  (~3.7 min)
│   │   Fiber: flat tip 200μm/0.37NA, 0.3–0.5mm lateral from probe
│   │
│   ├── Power ramp
│   │       Rate       : 10 Hz
│   │       Pulse      : 5 ms  (offset artefact at 4.85ms — clear of 0.67ms spike)
│   │       Powers     : 1, 2, 5, 10, 20, 40, 56 mW
│   │       Pulses     : 200 → tapered to ~42 at max  (energy cap 12 mJ/level)
│   │       Purpose    : reliability vs power curve; distance/expression stratification
│   │
│   └── Following test
│           Rate       : 40 Hz and 60 Hz
│           Pulse      : 1 ms
│           Structure  : 10 trains × 20 pulses, 3 s ITI
│           Power      : fixed 10 mW  (suprathreshold)
│           Purpose    : confirm direct ChR2 drive; expect >80% at 40Hz,
│                        degraded at 60Hz (ChR2-H134R kinetic ceiling)
│
├── ANTIDROMIC BLOCK  (~5.2 min)
│   │   Fiber: at projection target (GPi / STN)
│   │
│   ├── Primary condition
│   │       Pulse      : 5 ms   (offset artefact at 4.85ms — clear of 1.26ms spike)
│   │       Power      : 62 mW  (mod=1.0; fiber-tip max — 80 mW not achievable)
│   │       Rate       : 20 Hz  (duty cycle 10%; collision + reliability)
│   │       Duration   : 3 min  →  3 600 pulses
│   │       Purpose    : reliability + collision accumulation
│   │
│   └── Crosscheck condition
│           Pulse      : 3 ms   (offset artefact shifted to 2.85ms)
│           Power      : 62 mW  (mod=1.0)
│           Rate       : 20 Hz  (duty cycle 6%)
│           Duration   : 2 min  →  2 400 pulses
│           Purpose    : artefact window displaced; catches any pulse-duration
│                        dependency in apparent latency distribution
│
└── CROSS-CUTTING DESIGN FEATURES
    │
    ├── Artefact management
    │       clearance_before   : 150 μs  (pre-stimulus blanking)
    │       clearance_after    : 250 μs  (post-onset/offset; validate at 80mW)
    │       Pulse duration chosen so offset artefact never overlaps
    │       expected spike latency window (somatic 0.67ms, antidromic 1.26ms)
    │
    ├── Classification criteria  (from GPe-PV literature)
    │       Latency            : < 2.5 ms
    │       Jitter             : < 0.1 ms  ← primary discriminator
    │       PETH z-score       : > 12
    │       Waveform corr.     : ≥ 0.85  (spontaneous vs light-evoked)
    │       Somatic following  : ≥ 80% at 10–40 Hz, < 80% at 60 Hz
    │
    ├── Collision test  (offline, antidromic candidates only)
    │       Accessible window  : ~0.31 ms  (1.26 − 0.8 − 0.15 ms)
    │       Feasible           : neurons ≥ 10 Hz spontaneous  (≥ 11 events / 3 min)
    │       Marginal           : 5–10 Hz  (5–11 events)
    │       Not feasible       : < 5 Hz  → latency/jitter criteria only
    │
    ├── Energy / heating
    │       Somatic   : 12 mJ cap per level; 10% duty cycle max
    │       Antidromic: 62 mW × 10% duty = 6.2 mW avg;
    │                   total ~1 566 mJ across both conditions
    │                   (stimulation site only — not at recording electrode)
    │
    └── Laser calibration  (Doric LDFL5_450, 473 nm)
            Two-step lookup  : mod (0–1) → Ia (mA) → mW
            Slope efficiency : 0.625 mW/mA above 18 mA threshold
            Note             : mod 0.25–0.28 spans 1–20 mW — DAC resolution
                               matters in this range; verify empirically
            Script           : scripts/opto_calibration.py
                               run: python scripts/opto_calibration.py [--save-dir DIR]
```

---

## Task config mapping

The session structure maps to `gpe_somatic` / `gpe_antidromic` task modes in
`/mnt/maindata/msw_configs/tasks/optotagging/task.yaml`.

Power ramp pulse counts per level (somatic, 12 mJ cap at 10 Hz / 5 ms):

| Power (mW) | Max pulses | Energy (mJ) |
|---|---|---|
| 1  | 200 | 1.0  |
| 2  | 200 | 2.0  |
| 5  | 200 | 5.0  |
| 10 | 200 | 10.0 |
| 20 | 120 | 12.0 |
| 40 |  60 | 12.0 |
| 56 |  43 | 12.1 |

Following test: 10 trains × 20 pulses = 200 pulses per frequency (40 Hz, 60 Hz).

Antidromic pulse counts:
- Primary (5 ms, 20 Hz, 3 min): 3 600 pulses
- Crosscheck (3 ms, 20 Hz, 2 min): 2 400 pulses
