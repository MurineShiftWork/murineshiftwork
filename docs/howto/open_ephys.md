# Record with Open Ephys

This guide covers running an MSW behaviour session alongside an Open Ephys
electrophysiology recording, with the two datastreams aligned by TTL barcodes.

Install the ephys extra:

```bash
pip install "murineshiftwork[oe]"
```

MSW controls the Open Ephys GUI remotely over its HTTP API. The full command
reference is on the [msw oe](../cli/oe.md) page; this page is the end-to-end
procedure.

---

## Wiring

Route the MSW barcode BNC output into a spare digital input on the Open Ephys
acquisition board so the ephys recording carries the same time anchors as the
behaviour session. See [Barcode Sync](barcode_sync.md) for the concept.

---

## 1. Start the ephys recording

Start Open Ephys as the session **host** so it owns the session container that
MSW and any other systems write into.

```bash
# Standalone ephys, or...
msw oe record --subject mouse001 --session-extension pxi

# ...a parent acquisition container that behaviour will join
msw oe record --subject mouse001 \
    --acquisition-extension ephys_multi_behavior \
    --session-extension pxi
```

On `record`, the plugin puts the GUI into `RECORD` and captures **probe
metadata** (probe count and channel/stream layout) live from the GUI's
`/api/processors` endpoint. That metadata is written to a session metadata JSON
and, when an `acquisition_manifest.yaml` is present, stamped into it under
`metadata.open_ephys`.

Check the state at any time:

```bash
msw oe status      # -> IDLE / ACQUIRE / RECORD
```

---

## 2. Run the behaviour session, attached to the host

Point `msw run` at the running Open Ephys host with `--host openephys`. MSW
attaches to the same session container and writes its behaviour acquisition
inside it, so ephys and behaviour share one session folder.

```bash
msw run -s mouse001 -t sequence --host openephys
# override the host address if it is not the machine default:
msw run -s mouse001 -t sequence --host openephys:10.0.10.111
```

Throughout the session MSW emits TTL barcodes on its BNC output, which the ephys
board records on the digital input wired in above.

---

## 3. Stop

Stop the behaviour session normally, then return the GUI to idle:

```bash
msw oe stop
```

---

## 4. Align offline

Decode the barcode edges recorded on the Open Ephys digital input and match them
to the behaviour barcodes to put ephys samples and trials on one timeline. The
procedure is described in [Barcode Sync](barcode_sync.md).

---

## See also

- [msw oe](../cli/oe.md) — full command reference
- [Barcode Sync](barcode_sync.md)
- [Multi-Acquisition & Photometry](../concepts/multi_acquisition_and_photometry.md)
