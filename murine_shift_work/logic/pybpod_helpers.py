def get_subject_from_pybpod_conf():
    from confapp import conf as confsett

    if len(confsett.PYBPOD_SUBJECTS) == 0:
        raise ValueError(
            "\n\n\tNo subjects in GUI settings. Is this a CLI call with is_cli_call=False upstream ?\n\n"
        )
    else:
        return eval(confsett.PYBPOD_SUBJECTS[0])[0]
