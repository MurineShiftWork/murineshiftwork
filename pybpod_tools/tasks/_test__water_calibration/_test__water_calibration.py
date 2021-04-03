# figure: show calibration curve raw and normalised by drops
# out data: dataframe of raw measurements. save to standard location
# out data: fitted curve for measurements
# -> save data at project level, but specify also board that was used and
# opening time + n_drops
#
# for drop in n_drops:
#     give drop
#     iti
#
# REPEAT for enough measurements to fit exponential
# TODO: IMPLEMENT
# TODO: ask for valve time, repeats, and water weight on command line with "input" function, then use plotext to plot curve for inspection which values to use next for full calibration
# TODO: implement line fit + save data + protocol needs to load calibration file and get correct value estimate from calibration curve

if __name__ == "__main__":
    print("main")
