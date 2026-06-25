# Sound Output

The reward/feedback sound is played through a low-latency output stream
(`StereoSound`). Most rigs use an **ASUS XONAR** sound card; the default device
name searched for is `XONAR SOUND CARD` (override with the `sound_device` key in
the setup config to pin an exact device).

## Windows 11 + XONAR: required driver settings

On Windows 11, audible, correct-speed playback at the full rate depends on three
XONAR driver / Windows settings. **All three must be set on each rig** — getting
any one wrong produces silent or distorted output:

| Setting | Required value | Symptom if wrong |
|---|---|---|
| **Channels** | **7.1** | partial / no output |
| **Sample rate** | **192000 Hz** — in *both* the XONAR driver output format *and* the Windows "Default Format" for the device | sound plays too slow / deflated, or is rejected |
| **Reverb / environment effect** | **ON, "studio" preset** | turning reverb fully *off* silenced the card under test; "studio" is near-dry and works |

The Windows default format and the XONAR driver output format must **match** at
192000 Hz. If they disagree, Windows resamples and the chirp comes out at the
wrong speed.

## How the app behaves

These code-side guards mean a misconfigured card degrades gracefully instead of
crashing the session, but they do **not** replace the driver settings above:

- **No `sysdefault` fallback.** If the configured device is not found, the app
  resolves PortAudio's real default output device (cross-platform), not the
  invalid `sysdefault` literal that was silent on Windows.
- **WASAPI shared mode** is used. WASAPI *exclusive* mode was silent on the
  XONAR output under test, so it is **not** auto-enabled (opt in per rig with
  `use_wasapi_exclusive: true` only if you have verified it).
- **Rate validation + fallback.** If the device rejects the configured rate
  (e.g. `192000` when the driver/Windows format is not at 192000, raising
  `PaErrorCode -9997`), the app falls back to the device's default rate so
  playback is correct-speed (audible) rather than deflated.
- **Adopts the stream's actual rate.** Sound is generated at the rate the
  output stream actually opened at, so it never plays slow/fast relative to the
  open stream.
- **Guarded playback.** A playback error is logged as a warning and never
  crashes the task thread.

## Verifying a rig

On session start, look for this log line — it reports the rate the stream
actually opened at:

```
StereoSound: persistent output stream open at <N> Hz (latency~<M> ms)
```

- `<N> = 192000` → full rate, driver triplet correct.
- `<N>` lower than expected (e.g. 48000) → the device rejected 192000 and fell
  back; playback will be correct-speed but not full-rate. Check the driver
  triplet above.

To characterise the true Bpod-state → sound-onset latency, run the
`_calibration_sound_latency` action (see
[Calibration & Test](../tasks/calibration_and_test.md)).
