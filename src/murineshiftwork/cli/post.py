"""msw post — post-acquisition data pipeline commands.

Commands:
  msw post clean   Remove known noise events from .msw.csv files (pure Python).
  msw post run     Orchestrate full post-acquisition pipeline (calls external scripts).
"""

import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def run_post_clean(**args_dict):
    """Remove noise-event rows from .msw.csv files under data_dir.

    Backs up each modified file as <file>.bak.<timestamp> before editing.
    """
    data_dir = Path(args_dict["data_dir"]).expanduser().resolve()
    event = args_dict.get("event", "Port4")
    dry_run = args_dict.get("dry_run", False)

    if not data_dir.exists():
        raise FileNotFoundError(f"data-dir not found: {data_dir}")

    csv_files = sorted(data_dir.rglob("*.msw.csv"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    n_scanned = 0
    n_modified = 0

    for f in csv_files:
        n_scanned += 1
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines(
            keepends=True
        )
        dirty = [line for line in lines if event in line]
        if not dirty:
            continue
        clean = [line for line in lines if event not in line]
        if dry_run:
            logging.info(f"[dry-run] would remove {len(dirty)} row(s) from {f}")
        else:
            shutil.copy2(f, f.with_suffix(f".bak.{ts}"))
            f.write_text("".join(clean), encoding="utf-8")
            n_modified += 1
            logging.info(f"Cleaned {len(dirty)} row(s): {f}")

    if dry_run:
        logging.info(f"Dry run complete. Scanned {n_scanned} file(s).")
    else:
        logging.info(f"Done. Scanned {n_scanned} file(s), modified {n_modified}.")


def run_post_run(**args_dict):
    """Orchestrate the post-acquisition data pipeline.

    Calls the shell script scripts/run_post_acquisition_tasks.sh, which in turn
    calls provision_rpi scripts for rsync, h264 conversion, and remote upload.
    Requires --provision-scripts pointing at the provision_rpi scripts directory.
    """
    import importlib.resources as pkg_resources

    # Locate the bundled shell script
    try:
        scripts_dir = (
            Path(pkg_resources.files("murineshiftwork")).parent.parent.parent
            / "scripts"
        )
        sh_script = scripts_dir / "run_post_acquisition_tasks.sh"
    except Exception:
        sh_script = (
            Path(__file__).parent.parent.parent.parent
            / "scripts"
            / "run_post_acquisition_tasks.sh"
        )

    if not sh_script.exists():
        raise FileNotFoundError(
            f"Pipeline script not found: {sh_script}\n"
            "Make sure the murineshiftwork source tree is intact."
        )

    cmd = ["bash", str(sh_script)]

    def _flag(key, dest):
        v = args_dict.get(key)
        if v:
            cmd.append(f"--{dest}={v}")

    _flag("central_data", "central-data")
    _flag("local_data", "local-data")
    _flag("provision_scripts", "provision-scripts")
    _flag("rpi_group", "rpi-group")
    _flag("setup_group", "setup-group")
    _flag("target_dir", "target-dir")

    for skip_flag in (
        "skip_upload",
        "skip_rpi",
        "skip_setups",
        "skip_h264",
        "skip_msw_clean",
    ):
        if args_dict.get(skip_flag):
            cmd.append(f"--{skip_flag.replace('_', '-')}")
    if args_dict.get("dry_run"):
        cmd.append("--dry-run")

    logging.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
