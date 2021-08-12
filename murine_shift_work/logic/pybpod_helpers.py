def get_subject_from_pybpod_conf():
    from confapp import conf as confsett

    return eval(confsett.PYBPOD_SUBJECTS[0])[0]
