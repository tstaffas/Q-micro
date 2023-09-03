#------IMPORTS-----
import Microscope_library as Q
#Packages for ETA backend
#import json
#import etabackend.eta   # Available at: https://github.com/timetag/ETA, https://eta.readthedocs.io/en/latest/
#from pathlib import Path
#from matplotlib import pyplot as plt
#import numpy as np
#import os


# ------------ PARAMETERS AND CONSTANTS --------------
eta_recipe = 'multiframe_recipe_bidirectional_segments_0.0.4.eta'        # 'microscope_bidirectional_segments_0.0.3.eta'

# Parameters to locate timeres files:
folder = "Data/230828/"             # Note: this is used to find the timeres file --> WRITE in your own data folder location
clue = "digit_6"                    # Note: this is used to help find the correct timeres file when only given frequency (ex: 'higher_power', 'digit_8', '13h44m23s')
#       ^ex. for data in "230828": {"digit_6"}

timetag_file = None                 # Note: let this be None if you want to use "clue" and "folder" to automatically find your file based on frequency
#timetag_file = 'Data/230828/digit_6_sineFreq(10)_numFrames(10)_sineAmp(0.3)_stepAmp(0.3)_stepDim(100)_date(230828)_time(10h28m37s).timeres'

# Scan parameters:
nr_frames = 10   # OBS: SET VALUE TO USE DATAFILE
freq = 10        # OBS: SET VALUE TO USE DATAFILE
ampX = 0.3                      # --> step values between -0.3 and 0.3
ampY = 0.3                      # --> sine values between -0.3 and 0.3
dimX = 100                      # how many (stepwise) steps we take in scan
bins = 20000                    # how many bins/containers we get back for one period   #20000 is good --> 10k per row
ch_sel = "h2"

# ------------ RELATIONSHIPS ------------
dimY = int(round(dimX*(ampY/ampX)))     # How many pixels we want to use TODO: Get new data (where ampX != ampY) and test this relationship!
freq_ps = freq * 1e-12                  # frequency scaled to unit picoseconds (ps)
period_ps = 1/freq_ps                   # period in unit picoseconds (ps)
binsize = int(round(period_ps/bins))    # how much time (in ps) each histogram bin is integrated over (=width of bins). Note that the current recipe returns "bins" values per period.
frame_duration = dimX / freq            # total frame time = (period) * (number of x steps)
fps = freq / dimX                       # fps = (1/frame_duration) = (freq / dimX)

print("bins =", bins, " ,  binsize =", binsize*10e-12, "seconds")
print(f"frame duration: {frame_duration} seconds\n --> {fps} fps")

# NOTE: Below is a dictionary with all the parameters defined above. This way we can sent a dict with full access instead of individual arguments
const = {
    "eta_recipe"       : eta_recipe,
    "timetag_file"     : timetag_file,
    "clue"             : clue,
    "folder"           : folder,
    "nr_frames"        : nr_frames,
    "freq"             : freq,
    "ampX"             : ampX,
    "ampY"             : ampY,
    "dimX"             : dimX,
    "bins"             : bins,
    "ch_sel"           : ch_sel,
    "dimY"             : dimY,
    "freq_ps"          : freq_ps,
    "period_ps"        : period_ps,
    "binsize"          : binsize,
    "frame_duration"   : frame_duration,
    "fps"              : fps,
    }


# --------- GET DATA AND HISTOGRAMS------------

# quick version of "ad infinitum" code where we generate one image/frame at a time from ETA
if __name__ == "__main__":

    # --- GET TIMETAG FILE NAME, unless manually provided ---
    if timetag_file is None:
        timetag_file = Q.get_timres_name(folder, nr_frames, freq, clue=clue)
        const["timetag_file"] = timetag_file

    # --- PROVIDE WHICH MAIN FOLDER WE SAVE ANY ANALYSIS TO FOR THE USED ETA FILE (ex. images, raw data files, etc.)
    st = timetag_file.find("date(")
    fin = timetag_file.find(".timeres")
    const["save_location"] = f"Analysis/({str(freq)}Hz)_{timetag_file[st:fin]}"   # This is the folder name for the folder where data, images, and anything else saved from analysis will be saved
    #       FOR EXAMPLE: const["save_location"] = Analysis/(100Hz)_date(230717)_time(14h02m31s)

    # --- EXTRACT AND ANALYZE DATA ---
    Q.eta_segmented_analysis_multiframe(const=const)   # note: all params we need are sent in with a dictionary. makes code cleaner


