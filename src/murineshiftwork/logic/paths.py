import socket
from pathlib import Path

from murineshiftwork.namespace.paths import (
    _FORBIDDEN_PATH_CHARS,
    CURRENT_NAMESPACE_VERSION,
    MSW_DATETIME_FORMAT,
    NAMESPACE_LEGACY,
    NAMESPACE_V1,
    build_data_paths,
    generate_session_paths,
    parse_session_basename,
)

__all__ = [
    "CURRENT_NAMESPACE_VERSION",
    "MSW_DATETIME_FORMAT",
    "NAMESPACE_LEGACY",
    "NAMESPACE_V1",
    "_FORBIDDEN_PATH_CHARS",
    "build_data_paths",
    "generate_session_paths",
    "parse_session_basename",
    "test_path_is_writable",
    "get_host_ip",
    "get_host_name",
]


def test_path_is_writable(path=None):
    try:
        with open(path, "w"):
            pass
        if Path(path).exists():
            Path(path).unlink()
    except PermissionError:
        return False
    return True


def get_host_ip():
    """Source: https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP


def get_host_name():
    return socket.gethostname()
