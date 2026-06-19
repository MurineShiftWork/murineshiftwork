# Murine Shift Work

Behaviour acquisition framework for standardised, scalable experiments.

```bash
msw run --setup rig-a --subject mouse001 --task sequence
```

---

## What it does

- **Behavioural tasks**: sequence learning, probabilistic switching, optotagging, calibration routines
- **Hardware abstraction**: interchangeable backends for behaviour controllers, cameras, stage, scale, stimulators
- **Config system**: layered YAML overrides (bundled defaults, rig overlay, task mode, subject, CLI)
- **Session files**: structured `.msw.session.yaml` + JSONL trial data; reader API for analysis
- **Live plot**: per-task online performance display during acquisition
- **TTL barcodes**: unique per-trial barcodes on BNC output for alignment with parallel recordings

---

## Installation

Requires Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
pip install murineshiftwork
```

### First-time setup

```bash
msw init --config-dir /path/to/msw_configs
msw setup create rig-a
msw subject add -s mouse001
```

---

## Development

```bash
git clone https://github.com/MurineShiftWork/murineshiftwork.git
cd murineshiftwork
uv sync --group dev
uv run pytest tests/
```

Pre-commit hooks (ruff, mypy, secrets scan):

```bash
pre-commit install
```

---

## Docs

See `docs/` for CLI reference, config system, session files, and task guides.
Key architecture decisions are in `docs/MASTER_PLAN.md`.

---

## License

Copyright © 2021-2026 Lars B. Rollik.
See [LICENSE](LICENSE) for terms.
