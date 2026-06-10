# Security Review — Pre-public Release

Audit run: 2026-06-10. To be resolved before pushing public orphan branch.

---

## Critical: Real lab IPs exposed

| File | IP / content | Action |
|---|---|---|
| `msw-open-ephys/README.md` | `172.24.242.168` ×7 | **Fixed** → `10.0.10.111` |
| `src/murineshiftwork/cli/parser.py:90` | `172.24.42.168` in `--host` help text | Replace with `10.0.10.111` |
| `src/murineshiftwork/hardware/host_session.py:19` | `172.24.42.168` in docstring example | Replace |
| `docs/cli/run.md:32` | `172.24.42.168` in table | Replace |
| `docs/setup/setup_config.md:169` | `172.24.42.168` in YAML example | Replace |
| `docs/setup/DHCP.md` | Full MAC table, real IPs, machine names, usernames | Move upstream with docs |
| `docs/work_plans/PROVISION_RPI_SCRIPTS.md` | `/home/murinemanager/`, Ceph cluster path, Ansible users | Move upstream with docs |
| `docs/work_plans/MASTER_PLAN.md:254` | `172.24.42.168` in YAML example | Move upstream |
| `playground/` (125 files) | Internal config paths, `murinemanager` hostname | Move upstream with docs |

**Note:** `docs/` and `playground/` will move upstream into the project-dir layout (not into the public repo). Only `src/` files need scrubbing before the orphan push.

---

## Medium: Protonmail address in tracked files

| File | Content |
|---|---|
| `.copier-answers.yml` | `author_email: L.B.Rollik@protonmail.com` |
| `CODE_OF_CONDUCT.md:63` | Contact for code of conduct violations |
| `docs/work_plans/BUILD_SYSTEM_STANDARD.md` | Copier template example |

Fix: replace with `lars@rollik.me` throughout. These files go into the public repo.

---

## Low: Network topology in docs (moving upstream)

- `docs/setup/DHCP.md` — 30+ RPi identifiers with physical camera locations, `epsilon`, `hermes`, `rtpp` hostnames, `murinemanager` username
- Internal network ranges `172.24.x.x` and `192.168.100.x` throughout DHCP.md

These are covered by the docs → project-dir move. No action in repo.

---

## Open Ephys API security

The OE HTTP API (port 37497) has no authentication — designed for trusted local network only.

Mitigations to document:
1. OE machines must be on firewalled internal VLAN (no external route to port 37497)
2. Firewall rule on OE machine: restrict port 37497 to lab subnet
3. `msw-open-ephys` is client-side only; nothing to secure in the package itself

---

## Pre-public checklist

- [x] `msw-open-ephys` README IPs replaced
- [ ] `src/` files: replace `172.24.42.168` → `10.0.10.111` in parser.py, host_session.py
- [ ] `docs/cli/run.md`, `docs/setup/setup_config.md`: replace IP examples
- [ ] `.copier-answers.yml`, `CODE_OF_CONDUCT.md`, `BUILD_SYSTEM_STANDARD.md`: fix email
- [ ] `CONTRIBUTING.md`: confirm no internal paths (done — off-limits section removed)
- [ ] Confirm `docs/` and `playground/` are excluded from the public orphan branch
