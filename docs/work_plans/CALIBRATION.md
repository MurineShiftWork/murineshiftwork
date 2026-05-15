# Calibration

## Water / valve calibration

### Overview

Each Bpod valve port is calibrated by dispensing a known number of drops at several
valve opening times, weighing the total dispensed volume on the serial scale, and fitting
an interpolation curve (valve_opening_time_ms → volume_µl).

Calibration data is saved as CSV at the path passed via `-cwater`. The curve is used at
session start by `water_volume_to_valve_time()` to convert target volume (µl) into the
opening time loaded into state machine output actions.

### Valve selection (current limitation — needs improvement)

The task currently hard-codes `VALVES_TO_CALIBRATE = [1, 3]` in
`tasks/calibrate_water_with_serial_scale/calibrate_water_with_serial_scale.py`.

**Required: add CLI / task-settings input for valve selection:**

| Input | Behaviour |
|---|---|
| `-valve 2` | Calibrate only valve 2 |
| `-valve 1 3` | Calibrate valves 1 and 3 |
| `-valve all` (default) | Calibrate all reward ports available on the connected Bpod |

"All available ports" is determined from the Bpod hardware info returned on connection
(`bpod.hardware.outputs` / port count). Once `SetupConfig` is wired in, the valve list
can also come from `setup.calibrations.bpod_valve.keys()`.

### Calibration parameters (all should be task.settings, not hardcoded)

| Parameter | Current value | Notes |
|---|---|---|
| `VALVE_TIME_MIN` | 10 ms | Shortest opening time to test |
| `VALVE_TIME_MAX` | 100 ms | Longest opening time to test |
| `VALVE_TIME_STEP` | 20 ms | Step between test points |
| `N_DROPS` | 400 | Drops per calibration point; drives accuracy vs time |
| `INTER_PULSE_INTERVAL` | 0.15 s | Inter-drop interval; must exceed valve close time |

### Serial scale speed — root cause and fixes

Scale hardware: custom HX711-based Arduino (firmware in
`/mnt/maindata/code/serial_weighing_scale/scale_firmware/scale_firmware.ino`).

**Root cause of 10–20 s initialisation and non-decodable (NaN) readings:**

The firmware `LoadCell.start(STABILIZING_TIME=2000, PERFORM_TARE=true)` in `setup()`
**blocks the Arduino for 2+ seconds**. During this time the main loop does not run and
no serial commands are processed. Python connects immediately and starts polling — each
`readline()` has a 1 s timeout, so 2 reads time out (returning empty string) before the
Arduino is ready. `float("")` raises `ValueError` → `read_weight()` returns `None` →
`is_ready` returns `False`. The `start()` loop has a 10 s timeout (= 5 × 2 s per
iteration), and the calibration task adds a second `while not scale.is_ready` loop on
top — giving 10–20 s total.

**This is not an 80 Hz / sampling rate issue.** The Timer1 interrupt only drives
`LoadCell.update()`, which itself only returns `true` when the HX711 hardware has new
data. With RATE pin LOW the HX711 outputs at 10 Hz regardless of how fast the firmware
polls. Changing the timer frequency alone does nothing; 80 Hz requires pulling the RATE
pin HIGH in hardware.

**Fix (implemented in firmware v2.1.0 + Python):**

Three coordinated changes:

**1. Firmware: non-blocking init** (`scale_firmware.ino`)

`setup()` now calls `LoadCell.startNoDelay(500, PERFORM_TARE)` instead of the blocking
`LoadCell.start(2000, ...)`. `setup()` returns in microseconds. The Timer1 ISR (already
running at 10 Hz) drives `LoadCell.update()` in `loop()`. The tare completes within
~500 ms of power-on. Until `getTareStatus()` returns true, `loop()` returns early and
all incoming serial bytes are discarded. Once done, `initDone = true` and normal command
processing begins.

**2. Python: prevent DTR-triggered Arduino reset** (`connection.py`)

```python
Serial(port=..., baudrate=..., timeout=..., dsrdtr=False, rtscts=False)
```
pyserial's default behaviour toggles the DTR line on `Serial.open()`. On Uno/Nano boards
the DTR pin is connected to RESET via a 100 nF capacitor — toggling it resets the Arduino,
causing the init to run again on every Python connection. `dsrdtr=False` prevents this.

If a reset does occur (some OS drivers ignore this flag during enumeration), the firmware
re-runs init and completes in <500 ms.

**3. Python: poll identify() not read_weight()** (`scale.py`)

`Scale.start()` now polls `identify()` (sends `<i>`, checks response) instead of
`is_ready` (which hammered `<w>` and got garbage during init). The firmware only responds
to `<i>` once `initDone` is true, so the poll naturally converges in ≤500 ms without
spurious NaN errors.

**Note on 80 Hz:** The HX711 RATE pin (hardware) controls the ADC rate — LOW = 10 Hz,
HIGH = 80 Hz. 80 Hz mode is stable and widely used; noise per sample is ~3.5× higher
but for gram-scale water calibration measurements this is negligible. A hardware RATE
pin change combined with firmware timer update would give faster weight settling, but
this is a secondary improvement and requires board modification. Address the startup
timing issues above first.

---

## Sound calibration

### Overview

Sound playback has a latency between the Bpod softcode that triggers the soundcard and
the TTL rising edge received back at Bpod BNC-in (confirming the card started playing).
This delay must be measured and compensated so trial timing is accurate.

Calibration data is saved as CSV at the path passed via `-csound` (currently
`calibration.sound.default.csv` in `~/.murineshiftwork/`).

### What is measured

| Field | Description |
|---|---|
| `trial` | Trial index |
| `delay` | Time (s) from Bpod softcode send to BNC-in TTL received |

The correction value is the **median delay** across trials:
```python
CalibrationDataSound.calculate_sound_delay_correction()  # → median delay in seconds
```
This value is subtracted from the scheduled sound trigger time in state machines that
require tight audio-behavioural alignment.

### Wiring requirement

```
Soundcard audio out → speaker
Soundcard TTL/trigger out → Bpod BNC-in 1 (or 2)
```

The BNC-in channel number is set in `task.settings` as `HARDWARE_BNC_SOUND_TTL_IN`.
The calibration task sends a softcode, starts a Bpod timer, and waits for the BNC edge.
Delay = time from softcode to state change on BNC-in.

### When to recalibrate

- After changing soundcard, audio driver, or OS audio settings
- After significant system load changes (e.g., adding GPU workloads)
- Delays are typically 5–30 ms and stable within a session; recalibrate if median shifts
  by more than 2 ms between sessions.
