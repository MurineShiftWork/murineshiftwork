# msw calibration

Plot and save valve calibration curves as PDF.

```
msw calibration plot [--setup <name>] [--out <dir>] [--config-dir <dir>]
```

The `plot` positional argument is required (it is the only action currently supported).

## Options

| Flag | Description |
|---|---|
| `--setup <name>` | Limit output to one setup (default: all setups) |
| `--out <dir>` | Where to write PDFs (default: `.`) |
| `-cd / --config-dir <dir>` | Config directory (default: from machine config) |

## Example

```bash
# Plot all setups
msw calibration plot --out ~/calibration_plots/

# Single setup
msw calibration plot --setup setup_a --out ~/calibration_plots/
```

For the calibration procedure, see [Tutorial: Valve Calibration](../tutorials/calibration.md).
