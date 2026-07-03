# Photometry (planned)

!!! warning "Design stage"
    Fibre-photometry integration is **not fully shipped**. MSW provides the
    building blocks (a shared session container, an acquisition manifest, and TTL
    barcode sync), but there is no turnkey `msw` photometry command or bundled
    photometry host plugin yet. This page describes the intended approach and the
    current limitations. For the full design discussion see
    [Multi-Acquisition & Photometry](../concepts/multi_acquisition_and_photometry.md).

---

## Intended approach

Photometry is treated as a second acquisition recorded in parallel with MSW
behaviour inside a shared session container, aligned afterwards by TTL barcodes.
Two integration levels are envisaged:

### Passive parallel recording (recommended starting point)

MSW and the photometry system record independently. MSW emits TTL barcodes on a
BNC output; the photometry rig records the same barcode line on a digital input.
The photometry files are saved into a parallel acquisition folder inside the MSW
session container, and the barcodes align the two streams offline — no direct
software coupling required. See [Barcode Sync](barcode_sync.md).

```
<session_container>/
├── acquisition_manifest.yaml
├── <msw_behaviour_acquisition>/     ← MSW behaviour
└── <photometry_acquisition>/        ← photometry, aligned via barcodes
```

### Photometry as an MSW host plugin

If the photometry system exposes an API (HTTP/ZMQ), it can implement the MSW
`HostSessionProtocol` and register a `msw.host` entry point, so `msw run --host
photometry:<url>` attaches recording lifecycle to the task. This path is
sketched in the concept page but is not shipped as a bundled plugin.

---

## Current limitations

- **No bundled photometry command or plugin.** There is no `msw photometry`
  subcommand and no shipped photometry host plugin; the passive-recording path
  above is the practical option today.
- **Single host per run.** Only one `--host` may be attached to a run, so
  photometry-as-host and Open Ephys-as-host cannot both be plugins in the same
  session. Use passive parallel recording for the second system.
- **No cross-acquisition alignment helpers.** MSW supplies TTL barcodes as the
  alignment primitive; automatic cross-stream timestamp alignment is not yet part
  of the MSW post-processing API. Decode and align with `ttl-barcoder` directly.

---

## See also

- [Multi-Acquisition & Photometry](../concepts/multi_acquisition_and_photometry.md) — full design
- [Barcode Sync](barcode_sync.md)
- [Record with Open Ephys](open_ephys.md)
