import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


session_name = "20210411-103143"

f = f"/home/lbr/code/pybpod_lbr/main_project/experiments/MAIN_experiment/setups/MAIN_setup/sessions/{session_name}/{session_name}.csv"
data = pd.read_csv(str(f), header=6, delimiter=";")

filt1 = data.loc[data["+INFO"].notnull()]
filt2 = filt1.loc[
    filt1["+INFO"].str.contains("|".join(["Port2Out", "Port1In", "Port3In"]))
]

outbound_travel = []
for ir1, ir2 in zip(filt2[:-1].iterrows(), filt2[1:].iterrows()):
    if ir1[-1]["+INFO"] == "Port2Out" and (
        ir2[-1]["+INFO"] == "Port1In" or ir2[-1]["+INFO"] == "Port3In"
    ):
        travel_time = round(
            ir2[-1]["BPOD-INITIAL-TIME"] - ir1[-1]["BPOD-INITIAL-TIME"], 3
        )
        if np.abs(travel_time) < 5:
            outbound_travel.append(travel_time)
        print(ir1[-1]["+INFO"], "-->", ir2[-1]["+INFO"], "DIFF:", travel_time)

r = [0, 2]
bins = 50
xticks = 10
plt.hist(outbound_travel, bins=bins, range=r)
plt.xticks(np.linspace(*r, xticks - 1, endpoint=True))
plt.xlim(*r)
plt.show()
