"""Session path and metadata management for Open Ephys recordings.

Three session modes, selected by arguments:

  Standalone  (no --acquisition-extension, no --child)
    OE records to:  {remote_path}/{subject__dt__session_ext}/Record Node/
    Local metadata: {local_path}/{subject}/{subject__dt__session_ext}/

  Parent      (--acquisition-extension is set, no --child)
    OE records to:  {remote_path}/{subject__dt__acq_ext}/{subject__dt__session_ext}/Record Node/
    Local metadata: {local_path}/{subject}/{subject__dt__acq_ext}/
    Caches acquisition_name for --child @last.

  Child       (--child <acq_name> or --child @last)
    OE records to:  {remote_path}/{acq_name}/{subject__dt__session_ext}/Record Node/
    Local metadata: {local_path}/{subject}/{acq_name}/

Remote path design
------------------
The OE GUI only creates the final leaf of parent_directory (cannot create
intermediate dirs). To work around this, remote_path is always used as
parent_directory on the Record Node (it already exists), and the full
subdirectory hierarchy is written into base_text using forward slashes.
OE accepts forward-slash paths in base_text on Windows and creates all
levels correctly.

  parent_directory = remote_path          (always, set per Record Node)
  base_text        = acq_name/session_name (set globally via /api/recording)

The cache stores acquisition_name (no subject prefix) so --child @last
maps directly to the base_text prefix for child sessions.
"""

import time
from pathlib import Path

from oe_remote._version import __version__ as METADATA_VERSION

_SESSION_CACHE = Path.home() / ".cache" / "oe-remote" / "last_session"


class Session:
    """Encapsulates all naming, path, and metadata logic for one recording."""

    def __init__(
        self,
        subject: str,
        session_extension: str,
        local_path: str,
        remote_path: str,
        ip: str,
        port: int,
        acquisition_extension: str = "",
        is_child_session_to: str = "",
    ):
        self.subject = subject
        self.session_extension = session_extension
        self.acquisition_extension = acquisition_extension
        self.local_path = Path(local_path)
        self.remote_path = remote_path.rstrip("/\\")
        self.ip = ip
        self.port = port
        self.is_child_session_to = is_child_session_to

        self.dt = time.strftime("%Y%m%d_%H%M%S")
        self.session_name = f"{subject}__{self.dt}__{session_extension}"
        self.acquisition_name = (
            f"{subject}__{self.dt}__{acquisition_extension}"
            if acquisition_extension
            else self.session_name
        )

        self._compute_paths()

    def _compute_paths(self) -> None:
        # parent_directory is always the top-level remote path (known to exist).
        # base_text carries the full subdirectory hierarchy with forward slashes;
        # OE creates all levels when recording starts.
        self.parent_directory = self.remote_path

        if self.is_child_session_to:
            # Case 3 – child
            self.local_path_full = (
                self.local_path / self.subject / self.is_child_session_to
            )
            self.base_text = f"{self.is_child_session_to}/{self.session_name}"
            self.main_session_folder = self.base_text
            self._cache_path = self.is_child_session_to

        elif self.acquisition_extension:
            # Case 2 – parent
            self.local_path_full = (
                self.local_path / self.subject / self.acquisition_name
            )
            self.base_text = f"{self.subject}/{self.acquisition_name}/{self.session_name}"
            self.main_session_folder = self.base_text
            self._cache_path = self.acquisition_name

        else:
            # Case 1 – standalone
            self.local_path_full = (
                self.local_path / self.subject / self.session_name
            )
            self.base_text = f"{self.subject}/{self.session_name}"
            self.main_session_folder = self.session_name
            self._cache_path = self.session_name

    @property
    def metadata_file(self) -> Path:
        return self.local_path_full / f"{self.session_name}.settings.ephys.json"

    def metadata(self, oe_state: dict = None) -> dict:
        """Full metadata dict for the .settings.ephys.json file.

        All keys from metadata_version 2 are preserved for backward compatibility.
        Branch on ``metadata_version`` to handle format differences.
        """
        return {
            # --- Version ---
            "metadata_version": METADATA_VERSION,
            "version": METADATA_VERSION,              # legacy key (was 2)
            # --- Identity ---
            "subject": self.subject,
            "datetime": self.dt,
            "acquisition_extension": self.acquisition_extension,
            "session_extension": self.session_extension,
            "acquisition_name": self.acquisition_name,
            "session_name": self.session_extension,       # legacy: stored extension string
            "full_session_name": self.session_name,       # full subject__dt__ext string
            "full_acquisition_name": self.main_session_folder,   # legacy alias
            "main_session_folder": self.main_session_folder,
            "acquisition_task_name": self.acquisition_extension,  # legacy alias
            "is_child_session_to": self.is_child_session_to,
            # --- Local paths ---
            "local_path": str(self.local_path),
            "local_path_full": str(self.local_path_full),
            "metadata_file": str(self.metadata_file),
            # --- Remote / OE recording settings ---
            "remote_ip": self.ip,
            "remote_port": self.port,
            "remote_path": self.remote_path,
            "parent_directory": self.parent_directory,
            "base_text": self.base_text,
            "prepend_text": "",
            "append_text": "",
            "create_new_dir": True,
            # --- OE live state snapshot (populated after recording starts) ---
            "oe_settings": oe_state or {},
        }

    # ------------------------------------------------------------------
    # Session cache — always written so --child @last works after any record
    # ------------------------------------------------------------------

    def save_to_cache(self) -> None:
        _SESSION_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _SESSION_CACHE.write_text(self._cache_path)

    @staticmethod
    def resolve_child(value: str) -> str:
        """Expand '@last' to the cached path, or pass value through."""
        if value != "@last":
            return value
        if not _SESSION_CACHE.exists():
            raise FileNotFoundError(
                "No cached session found. Run any 'record' command first, "
                "or pass the acquisition name explicitly to --child."
            )
        return _SESSION_CACHE.read_text().strip()
