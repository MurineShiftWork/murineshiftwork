import os


def softcode_handler(task_object=None, code=None):
    if code == 0:
        pass  # some init tasks
    elif code == 1:
        task_object.play_go_cue()
    elif code == 2:
        task_object.play_stop_cue()
    elif code == -1:
        task_object.stop_sound()


def unpack_input_dict(default_dict, overwrite_dict):
    for k, v in overwrite_dict.items():
        default_dict[k] = v
    return default_dict


def get_session_file_basename(bpod=None):
    return os.path.splitext(bpod.session._path)[0]


def make_protocol_identifier_ttl_sequence(bpod=None, sequence=None):
    sma = None  # FIXME: add state machine for TTL sequence
    return sma
