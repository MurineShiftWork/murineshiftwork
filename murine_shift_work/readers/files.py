import json
import logging
import os
import subprocess
from glob import glob
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pandas as pd


def _exec_sys_cmd(cmd=None, shell=True, stdout=subprocess.PIPE):
    """

    :param cmd:
    :param shell:
    :param stdout:
    :return:
    """
    return (
        subprocess.Popen(cmd, shell=shell, stdout=stdout)
        .stdout.read()
        .decode()
        .strip("\n")
    )


def read_settings_py(file=None):
    tmp_module = SourceFileLoader(
        os.path.splitext(Path(file).name)[0], str(file)
    ).load_module()
    module_vars = {k: v for k, v in vars(tmp_module).items() if not k.startswith("__")}
    return module_vars


def read_json(file=None):
    with open(file, "r") as f:
        data = f.read()
    return json.loads(data)


def read_pybpod_csv(filepath=None, clean_events=True, return_trial_structure_only=True):
    """Read csv file from pybpod acquisition.
    Optional: clean up irrelevant events, but make backup with sed.
    """
    # Clean file
    backup_file = glob(str(Path(filepath).parent / "*.csv.bak.*"))
    if clean_events and len(backup_file) == 0:
        current_dt = _exec_sys_cmd("date +%Y%m%d_%H%M%S")
        cleaning_cmd = f"sed '-i.bak.{current_dt}' '/Port4/d' {str(filepath)}"
        report = _exec_sys_cmd(cmd=cleaning_cmd)
        if report:
            raise SystemError(f"Command returned error: {report}")
        logging.debug(f"{Path(filepath).name} - File cleaned before import.")

    # Load raw csv
    session_raw = pd.read_csv(
        filepath, delimiter=";", header=6, infer_datetime_format=True
    )
    session_raw.rename(columns={"PC-TIME": "TS"}, inplace=True)
    session_raw[["TYPE", "MSG", "+INFO"]] = session_raw[
        ["TYPE", "MSG", "+INFO"]
    ].astype("string")

    logging.debug(
        f"{Path(filepath).name} - Applying datetime conversion to {session_raw.shape[0]} rows.."
    )

    if return_trial_structure_only:
        session_raw = session_raw.loc[session_raw["+INFO"].isna(), :]
    else:
        session_raw["TS"] = session_raw["TS"].apply(
            lambda x: pd.to_datetime(x).to_pydatetime()
        )
    return session_raw


def __dict_series_to_pd_columns(df=None, column=None):
    tmp = pd.DataFrame(df[column].to_list())
    return df.drop(column, axis=1).join(tmp)


def read_trial_df(
    filepath=None,
    return_raw=False,
):
    df = pd.read_pickle(filepath)

    if df.empty or df.shape == (1, 1):
        logging.debug("df is empty or shape weird")
        return None

    # If only one column called "0", then is Series of disrupted session, not DataFrame
    columns = list(df.columns)
    if columns.__len__() == 1 and 0 in columns:
        logging.debug("df has only one column, which is 0")
        return None

    if return_raw:
        return df
    else:
        try:
            df = __dict_series_to_pd_columns(df=df, column="info")
            df = __dict_series_to_pd_columns(df=df, column="States timestamps")
            df = __dict_series_to_pd_columns(df=df, column="Events timestamps")
        except KeyError:
            logging.debug("KEY ERROR", filepath)
            return None

        # Column exists in acquisition, but not used in namespace.
        if "analysis" in df:
            try:
                df = __dict_series_to_pd_columns(df=df, column="analysis")
            except BaseException:
                df = df.drop("analysis", axis=1)

        return df
