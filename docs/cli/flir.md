# msw flir

FLIR machine-vision camera capture via Bonsai workflows. Provided by the
`msw-flir-bonsai` plugin, which registers a `flir` subcommand group with `msw`
and also ships a standalone `msw-flir` console script with the same
subcommands.

```
msw flir <command> [options]
```

The camera SDKs (FlyCapture2 / PyCapture2, or Spinnaker / PySpin) and Bonsai are
Windows-only, so the hardware commands run on the Windows acquisition host.

## Subcommands

| Command | Description |
|---|---|
| `find-bonsai` | Scan known install locations and print the `Bonsai.exe` path |
| `list-cameras` | List connected FLIR cameras with index and serial number |
| `run` | Launch one Bonsai process per camera and record until stopped |
| `test-record` | Short single-camera test recording to verify the setup |

## `find-bonsai`

Searches the standard install locations and prints the first `Bonsai.exe` found.
Copy the path into your setup YAML under `cameras.bonsai_exe`, or export it as
the `BONSAI_EXE` environment variable.

```bash
msw flir find-bonsai
```

## `list-cameras`

```bash
msw flir list-cameras [--driver flycap|spinnaker]
```

| Flag | Default | Description |
|---|---|---|
| `-d / --driver` | `flycap` | Camera driver: `flycap` (FlyCapture2) or `spinnaker` (Spinnaker SDK) |

Requires the matching SDK (PyCapture2 or PySpin) to be installed.

## `run`

Launches N independent Bonsai camera processes (one per camera index) and blocks
until every process exits or you press Ctrl+C.

```bash
msw flir run <output_dir> <session> [options]
```

| Argument / flag | Default | Description |
|---|---|---|
| `output_dir` | *(positional)* | Root directory for video output |
| `session` | *(positional)* | Session name (used for folder/file naming) |
| `-n / --n-cameras` | `1` | Number of cameras to launch |
| `-d / --driver` | `flycap` | Camera driver: `flycap` or `spinnaker` |
| `--fps` | `60` | Target frame rate (FlyCapture only) |
| `--bonsai-exe` | `$BONSAI_EXE` | Path to `Bonsai.exe` |
| `--workflow` | `run-flir-{driver}-1cam` | Override the Bonsai workflow stem |

Each camera writes to `<output_dir>/<session>/<session>.cam<i>`.

## `test-record`

Runs a fixed-duration recording from a single camera — useful for confirming a
camera index, frame rate, and output path before a real session.

```bash
msw flir test-record [--cam-index 0] [--driver flycap] [--fps 30] [--duration 5]
```

| Flag | Default | Description |
|---|---|---|
| `--output-dir` | `~/msw_flir_test` | Output directory |
| `--session` | `test` | Session name |
| `-c / --cam-index` | `0` | Camera index (0-based) |
| `--driver` | `flycap` | `flycap` or `spinnaker` |
| `--fps` | `30` | Target frame rate |
| `--duration` | `5.0` | Recording duration in seconds |
| `--bonsai-exe` | `$BONSAI_EXE` | Path to `Bonsai.exe` |

## Examples

```bash
# Locate Bonsai and list attached cameras
msw flir find-bonsai
msw flir list-cameras --driver flycap

# Record two cameras for a session
msw flir run D:\DATA\video mouse001 --n-cameras 2 --fps 60

# Quick 5 s sanity check on camera 0
msw flir test-record --cam-index 0 --duration 5
```

## See also

- [Cameras](../setup/cameras.md)
