"""Machine-local config at ~/.murineshiftwork/msw_machine.yaml.

Stores machine-specific settings that are independent of the shared config dir.
All external service URLs and credentials use a flat `<service>_api_<key>` naming
scheme so machine configs across rigs remain consistent.

Expected YAML structure (all keys optional):
    config_dir: /mnt/maindata/msw_configs
    data_dir: /mnt/maindata/data

    # MSW LogAgent / monitor backend  — the FastAPI ingest+query server;
    # msw-ui Vue SPA polls this for live session data
    logagent_api_url: http://monitor:8080
    logagent_api_token: <bearer-token>

    # MSW UI frontend — URL to open in browser (served by msw-ui nginx container)
    msw_ui_url: http://monitor:3000

    # Open Ephys remote control (fallback; prefer setup YAML open_ephys_url)
    openephys_api_url: <oe-host-ip>

    # labwatch session push — read by msw-labwatch, not by murineshiftwork core
    labwatch_api_url: https://labwatch.example.com
    labwatch_api_token: <token>

Priority for config_dir resolution (highest wins):
  1. CLI --config-dir argument
  2. MSW_CONFIG_DIR environment variable
  3. ~/.murineshiftwork/msw_machine.yaml `config_dir` key
  4. /mnt/maindata/msw_configs (historical default, if it exists)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

_MACHINE_CONFIG_FILE = Path.home() / ".murineshiftwork" / "msw_machine.yaml"
_HISTORICAL_DEFAULT = Path("/mnt/maindata/msw_configs")
_HISTORICAL_DATA_DEFAULT = Path("/mnt/maindata/data")


def _load_machine_config() -> dict:
    if _MACHINE_CONFIG_FILE.exists():
        try:
            with _MACHINE_CONFIG_FILE.open() as f:
                return yaml.safe_load(f) or {}
        except Exception as exc:
            logging.warning(
                f"Could not read machine config {_MACHINE_CONFIG_FILE}: {exc}"
            )
    return {}


def resolve_config_dir(cli_override: str = "") -> str:
    """Return the config dir to use, applying the priority chain.

    Args:
        cli_override: value of --config-dir from CLI (empty string = not set).
    """
    # 1. CLI explicit override
    if cli_override and not cli_override.startswith("unknown_"):
        return cli_override

    # 2. Environment variable
    env = os.environ.get("MSW_CONFIG_DIR", "").strip()
    if env:
        return env

    # 3. Machine config file
    mc = _load_machine_config()
    if mc.get("config_dir"):
        return str(mc["config_dir"])

    # 4. Historical default
    if _HISTORICAL_DEFAULT.exists():
        return str(_HISTORICAL_DEFAULT)

    return ""


def write_machine_config(config_dir: str | Path, **extra_fields) -> None:
    """Write (or update) ~/.murineshiftwork/msw_machine.yaml.

    Args:
        config_dir: path to the shared msw_configs directory.
        extra_fields: any additional machine-local key-value pairs.
    """
    _MACHINE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_machine_config()
    existing["config_dir"] = str(Path(config_dir).expanduser().resolve())
    existing.update(extra_fields)
    with _MACHINE_CONFIG_FILE.open("w") as f:
        yaml.dump(
            existing,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
    logging.info(f"Machine config written to {_MACHINE_CONFIG_FILE}")


def resolve_data_dir(cli_override: str = "") -> str:
    """Return the default data output directory, applying priority chain.

    Priority (highest first):
      1. --out-path CLI argument (passed as cli_override)
      2. MSW_DATA_DIR environment variable
      3. ~/.murineshiftwork/msw_machine.yaml ``data_dir`` key
      4. /mnt/maindata/data (historical default, if it exists)
      5. ~/data (fallback)
    """
    if cli_override and not cli_override.startswith("unknown_"):
        return cli_override

    env = os.environ.get("MSW_DATA_DIR", "").strip()
    if env:
        return env

    mc = _load_machine_config()
    if mc.get("data_dir"):
        return str(mc["data_dir"])

    if _HISTORICAL_DATA_DEFAULT.exists():
        return str(_HISTORICAL_DATA_DEFAULT)

    return str(Path.home() / "data")


def read_machine_config() -> dict:
    return _load_machine_config()


def read_ui_url() -> str:
    """Return the MSW UI frontend URL from machine config.

    Reads new-style key first, falls back to legacy:
      msw_ui_url (legacy: ui_url)
    """
    mc = _load_machine_config()
    return str(mc.get("msw_ui_url") or mc.get("ui_url", ""))


def read_log_config() -> dict:
    """Return LogAgent config from machine config.

    Reads new-style prefixed keys first, falls back to legacy names:
      logagent_api_url   (legacy: log_url)
      logagent_api_token (legacy: log_bearer_token)
    """
    mc = _load_machine_config()
    return {
        "log_url": mc.get("logagent_api_url") or mc.get("log_url", ""),
        "log_bearer_token": mc.get("logagent_api_token")
        or mc.get("log_bearer_token", ""),
    }


def read_open_ephys_url() -> str:
    """Return the Open Ephys GUI host from machine config (legacy fallback).

    Preferred location is the setup YAML ``open_ephys_url:`` field.
    Machine config is checked as a fallback; reads new-style key first:
      openephys_api_url (legacy: open_ephys_url)
    """
    mc = _load_machine_config()
    return str(mc.get("openephys_api_url") or mc.get("open_ephys_url", ""))


def get_machine_config_path() -> Path:
    return _MACHINE_CONFIG_FILE
