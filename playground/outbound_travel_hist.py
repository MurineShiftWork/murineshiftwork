import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

session_name = "20210417-155526"
setup_name = "MAIN"
f = f"/home/lbr/code/pybpod_lbr/main_project/experiments/{setup_name}_experiment/setups/{setup_name}_setup/sessions/{session_name}/{session_name}.csv"
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

r = [0.1, 0.5]
bins = int((r[1] - r[0]) / 0.005)
print(f"using {bins} bins.")
xticks = 10
plt.hist(outbound_travel, bins=bins, range=r)
plt.xticks(np.linspace(*r, xticks - 1, endpoint=True))
plt.xlim(*r)
plt.title(
    f"Session {session_name}. Center->Side travel. {len(outbound_travel)} trials < 2s."
)
plt.show()
