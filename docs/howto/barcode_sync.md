# Barcode Sync

TTL barcode synchronisation is how MSW aligns independent acquisition systems
offline. Instead of wiring every device to a shared clock, each system records
the same digital pulse trains, and post-hoc analysis matches them on the encoded
value. It is the primitive that lets Bpod behaviour, cameras (RCE), and
electrophysiology (Open Ephys / Neuropixels) be recorded on separate machines
and still be aligned to a common timeline.

The encoding and decoding live in the standalone
[`ttl-barcoder`](https://pypi.org/project/ttl-barcoder) package; MSW drives it
from `murineshiftwork.logic.barcode`.

---

## What a barcode is

A barcode encodes an integer as a timed sequence of HIGH/LOW pulses on a single
digital line:

- An **init pattern** marks the start of a barcode.
- The value is emitted as a **37-bit** word (the default), one bit per
  `bit_duration_ms` slot.
- By default the value is the **current Unix timestamp** quantised to
  milliseconds. Every barcode is therefore globally unique and self-describing:
  decoding it yields the wall-clock time the pulse train was emitted.

With the default preset (37 bits, 35 ms/bit) each barcode takes ~1.36 s to
transmit and the timestamp space covers ~4.4 years without wrap-around.

Because the payload is a timestamp, alignment does not depend on counting
pulses or on both systems seeing every barcode — any barcode present in two
recordings gives a shared, absolute time anchor.

---

## How MSW emits them

MSW injects barcode states into the Bpod state machine via
`ttl-barcoder`'s Bpod integration (`inject_barcode_states`). A barcode is emitted
on a BNC output at session start and at trial boundaries, so the behaviour
timeline carries periodic time anchors.

The barcode parameters come from the task settings and can be overridden per
task:

| Setting | Default | Meaning |
|---|---|---|
| `barcode_bits` | `37` | Word length (16–64 bits) |
| `barcode_bit_duration_ms` | `35.0` | Duration of one bit slot |
| `barcode_init_duration_ms` | `10.0` | Init-pattern pulse duration |
| `barcode_tolerance` | `0.25` | Fractional timing tolerance for decoding |

Some tasks also emit a short **identifier sequence** (e.g.
`probabilistic_switching` uses `sssLss`) so the task that produced a barcode
stream can be recognised in the recording.

The dedicated test/utility tasks make it easy to verify the wiring end to end:

```bash
msw run -s _test_subject -t _test_ttl_barcodes --simulate   # barcode output only
msw run -s _test_subject -t _test_barcode_iti               # barcode + ITI
msw run -s _test_subject -t _test_barcode_iti_with_video    # + camera capture
```

---

## Recording the barcodes on each system

Route the same BNC barcode line into a spare digital input on every system you
want to align:

- **Ephys (Open Ephys)** — record the barcode line on a digital input channel of
  the acquisition board. See [Record with Open Ephys](open_ephys.md).
- **Cameras (RCE)** — record the barcode line alongside frame capture so video
  frames carry the same anchors.
- **Photometry / other DAQ** — record the barcode line on any free digital
  input. See [Photometry (planned)](photometry.md).

No software coupling between the systems is required; they only need to see the
same pulses.

---

## Aligning offline

After acquisition, decode the pulse edges recorded by each system with
`ttl-barcoder`:

```python
from ttl_barcoder.core import BarcodeConfig
from ttl_barcoder.core.decoder import BarcodeDecoder

decoder = BarcodeDecoder(BarcodeConfig())      # match the recording's config
value = decoder.decode_edges(edge_times_ms)    # -> the encoded Unix timestamp
```

Each decoded barcode gives you a `(local_sample_time, unix_timestamp)` pair for
that system. Fitting local time against the shared timestamps for the barcodes
common to two recordings yields the transform that maps one system's clock onto
the other's, so trials, frames, and ephys samples land on one timeline.

Use the same `BarcodeConfig` (bit count, bit duration, tolerance) for decoding
that MSW used to emit — mismatched parameters will fail the init-pattern check.

---

## See also

- [Record with Open Ephys](open_ephys.md)
- [msw oe](../cli/oe.md)
- [Multi-Acquisition & Photometry](../concepts/multi_acquisition_and_photometry.md)
- [`ttl-barcoder` documentation](https://murineshiftwork.github.io/ttl-barcoder)
