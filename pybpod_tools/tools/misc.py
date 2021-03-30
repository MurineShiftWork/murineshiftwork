import os
from pkgutil import iter_modules


def unpack_input_dict(default_dict, overwrite_dict):
    for k, v in overwrite_dict.items():
        default_dict[k] = v
    return default_dict


def get_session_file_basename(bpod=None):
    return os.path.splitext(bpod.session._path)[0]


def list_submodules(module):
    submodules = []
    for submodule in iter_modules(module.__path__):
        submodules.append(submodule.name)
    return submodules
