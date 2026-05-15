"""Module-load-time defaults for the CLI.

Factored out of evaluate.py so parser.py can import them without importing the
full evaluate pipeline, avoiding any risk of a circular dependency.
"""
from murineshiftwork.logic.machine_config import resolve_config_dir, resolve_data_dir
from murineshiftwork.logic.misc import list_available_tasks

default_out_path = resolve_data_dir()
default_config_dir = resolve_config_dir()
available_tasks = "\n".join([f"    - {s}" for s in list_available_tasks()])
