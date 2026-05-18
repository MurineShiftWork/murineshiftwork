# msw calibration

Plot and save valve calibration curves as PDF.

```
msw calibration [--setup <name>] [--output-dir <dir>] [--config-dir <dir>]
```

## Options

| Flag | Description |
|---|---|
| `--setup <name>` | Limit output to one setup (default: all setups) |
| `--output-dir <dir>` | Where to write PDFs (default: `.`) |
| `--config-dir <dir>` | Config directory (default: from machine config) |

## Example

```bash
# Plot all setups
msw calibration --output-dir ~/calibration_plots/

# Single setup
msw calibration --setup setup_a --output-dir ~/calibration_plots/
```

For the calibration procedure, see [Tutorial: Valve Calibration](../tutorials/calibration.md).
