# RCE TTL — Migrate pigpio → lgpio

Working copy: `external/provision_rpi/rpi_camera_ensemble/`
Affects: `rpi_camera_ensemble/utils/ttl/`, `deploy.yaml`, `pyproject.toml`
Priority: **low** (no blocker on RPi 4 + Bookworm 32-bit; blocks RPi 5 support)
GitHub issue: **pending** — create on `murineshiftwork/rpi-camera-ensemble` after repo is public

Last updated: 2026-05-26

---

## Context

The `PigpioTTLEmitter` uses pigpio's DMA waveform engine for precise (~1 µs) GPIO pulses.
The actual use case is **camera-frame-driven sync pulses**: a Python callback fires on each
encoded frame and emits a TTL pulse (1 ms high, ≤200 Hz). At these parameters:

- Pulse interval ≥ 5 ms — orders of magnitude longer than scheduler jitter
- Acceptable jitter: ±50–100 µs (camera frame timing itself varies by this much)
- DMA waveforms are overkill and require an always-on root daemon

pigpio is effectively unmaintained (last release v79, 2021; apt package dropped from
Bookworm/Trixie; fundamentally incompatible with RPi 5). Full analysis:
`external/pigpio/ANALYSIS.md`.

**Decision**: replace with `lgpio` — the same author's chardev-based successor, pip-installable,
RPi 4 + RPi 5 compatible. Software-timed pulses at ≤200 Hz have ~10–50 µs jitter, which is
acceptable for hardware clock sync.

---

## Key files

| File | What changes |
|---|---|
| `rpi_camera_ensemble/utils/ttl/emitter.py` | Add `LgpioTTLEmitter`; register in `TTLEmitter._IMPLEMENTATIONS` |
| `rpi_camera_ensemble/utils/ttl/receiver.py` | Add `LgpioTTLReceiver` |
| `rpi_camera_ensemble/config/camera/camera.py` | Add `TTLLibrary.LGPIO` enum value |
| `pyproject.toml` | Add `lgpio` optional dep (new `[lgpio]` extra or rename existing) |
| `deploy.yaml` | Replace/remove pigpio build block; `pip install lgpio` in venv step |

---

## Implementation

### LgpioTTLEmitter

```python
class LgpioTTLEmitter(TTLDataMixin, TTLEmitterBase):
    """lgpio implementation — chardev-based, works on RPi 4 and RPi 5."""

    def _setup(self) -> None:
        import lgpio
        chip = self.kwargs.get("gpiochip", 0)   # RPi 4: 0, RPi 5: 4
        self._lgpio = lgpio
        self._h = lgpio.gpiochip_open(chip)
        lgpio.gpio_claim_output(self._h, self.pin)

    def _emit(self) -> None:
        # tx_pulse: high_us, low_us=0, pulse_off=0, count=1
        self._lgpio.tx_pulse(self._h, self.pin, self.duration_us, 0, 0, 1)

    def close(self) -> None:
        h = getattr(self, "_h", None)
        if h is not None:
            with contextlib.suppress(Exception):
                self._lgpio.gpiochip_close(h)
```

`tx_pulse` queues a non-blocking hardware pulse (high for `duration_us` µs, then low).
Returns immediately; the lgpio library drives the actual timing.

### LgpioTTLReceiver

Same pattern as `PigpioTTLReceiver` but using `lgpio.callback()` with `lgpio.EITHER_EDGE`.
lgpio callback timestamps use `time.time()` resolution (~1 µs), same as the current pigpio
implementation.

### gpiochip selection

RPi 4: GPIO is `/dev/gpiochip0`. RPi 5: GPIO is `/dev/gpiochip4` (RP1 southbridge).
Options (in order of preference):
1. **Auto-detect**: scan `/dev/gpiochip*`, pick the one labelled `pinctrl-rp1` or `pinctrl-bcm2711`
   via `lgpio.gpio_get_chip_info()` — most robust.
2. **Config field**: `gpiochip: 4` in the RCE agent config YAML — simple, explicit.
3. **Fallback to 0**: works on RPi 4, fails on RPi 5 with a clear error.

Recommended: config field with auto-detect as default.

---

## Deploy playbook changes (`deploy.yaml`)

Remove the entire `pigpio: build from source` block (lines ~108–155) and the
`pigpiod.service.j2` template deployment. Replace the pip install step:

```yaml
# was: rpi-camera-ensemble[acquisition,pigpio]
- name: Install rpi-camera-ensemble with lgpio into venv
  pip:
    name: "{{ remote_package_dir }}[acquisition,lgpio]"
    virtualenv: "{{ app_venv }}"
```

`lgpio` requires `libgpiod2` to be installed system-wide (usually already present on Bookworm).
Add to the apt packages list:

```yaml
- libgpiod2       # lgpio runtime dependency
```

The `pigpiod` systemd service and `/usr/local/bin/pigpiod` check can be removed entirely
once lgpio is the only backend in use. Keep them conditionally if pigpio fallback is desired
during a transition period.

---

## Open questions

1. **Backward compat**: should `TTLLibrary.PIGPIO` stay registered in the factory (as a
   deprecated path) for users who still have pigpiod? Probably yes, with a deprecation warning.
2. **lgpio version floor**: `tx_pulse` was added in lgpio 0.2. What is the earliest version
   available via PyPI? Check: `pip index versions lgpio`.
3. **RPi 5 CI**: no RPi 5 hardware in the current test matrix. lgpio path needs at minimum
   a mock/simulation test.
4. **Receiver jitter on RPi 5**: lgpio chardev callbacks on RPi 5 pass through the RP1 PCIe
   link. Edge detection latency is untested — may be higher than on RPi 4. Needs hardware
   measurement before relying on receiver timestamps for alignment.

---

## GitHub issue (to create after rpi-camera-ensemble repo is public)

**Title**: `feat: replace pigpio TTL backend with lgpio for RPi 5 compatibility`

**Body**:
> `PigpioTTLEmitter` / `PigpioTTLReceiver` rely on pigpio's DMA waveform engine, which
> requires `/dev/mem` access and a root daemon. pigpio is unmaintained (last release 2021)
> and architecturally incompatible with the RPi 5's RP1 GPIO chip (PCIe-mediated, no
> direct MMIO). See `external/pigpio/ANALYSIS.md` for the full technical breakdown.
>
> For the actual use case (camera-frame-driven sync pulses at ≤200 Hz, 1 ms duration),
> DMA precision is unnecessary. `lgpio` (chardev-based successor by the same author) gives
> ~10–50 µs jitter, acceptable for hardware clock synchronisation.
>
> Work plan: `docs/work_plans/PLAN_rce_ttl_lgpio.md`

Labels: `enhancement`, `rpi5`, `low-priority`
