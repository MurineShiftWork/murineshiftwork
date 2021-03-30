import os


def unpack_input_dict(default_dict, overwrite_dict):
    for k, v in overwrite_dict.items():
        default_dict[k] = v
    return default_dict


def get_session_file_basename(bpod=None):
    return os.path.splitext(bpod.session._path)[0]
