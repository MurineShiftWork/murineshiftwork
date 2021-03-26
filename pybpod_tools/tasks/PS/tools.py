def softcode_handler(task_object=None, code=None):
    if code == 0:
        pass  # some init tasks
    elif code == 1:
        task_object.play_go_cue()
    elif code == 2:
        task_object.play_stop_cue()
    elif code == -1:
        task_object.stop_sound()


def make_protocol_identifier_ttl_sequence(bpod=None, sequence=None):
    sma = None  # FIXME: add state machine for TTL sequence
    return sma
