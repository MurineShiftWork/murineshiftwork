

def softcode_handler(task_object=None, code=None):
    if code == 0:
        pass  # some init tasks
    elif code == 1:
        task_object.play_go_cue()
    elif code == 2:
        task_object.play_stop_cue()
    elif code == -1:
        task_object.stop_sound()
