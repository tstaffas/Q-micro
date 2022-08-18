#------IMPORTS-----
#Packages for ETA backend
import json
import etabackend.eta #Available at: https://github.com/timetag/ETA, https://eta.readthedocs.io/en/latest/
import etabackend.tk as etatk

#Packages used for analysis
import numpy as np
import numpy.ma as ma
from pathlib import Path
import os
import time as t

from matplotlib import pyplot as plt
import matplotlib.cm as cm

def ToF_analysis(timetag_file, recipe_file, ch_sel, **kwargs):
    load_start = t.time()
    #Load the recipe from seperate ETA file
    with open(recipe_file, 'r') as filehandle:
        recipe_obj = json.load(filehandle)

    eta_engine = etabackend.eta.ETA()
    eta_engine.load_recipe(recipe_obj)

    #Set parameters in the recipe
    for arg in kwargs:
        print(f'Setting {arg} as: {str(kwargs[arg])}')
        eta_engine.recipe.set_parameter(arg, str(kwargs[arg]))

    
    eta_engine.load_recipe()
    load_time = t.time() - load_start

    #---File handling---
    file = Path(timetag_file)

    #------ETA PROCESSING-----
    START = t.time()
    """
    Code block loads the time-tagging data and runs the ETA script to genereate ToF histograms
    """
    TOF_anal_start = t.time()
    print("Starting TOF analysis")
    cutfile = eta_engine.clips(file)
    result = eta_engine.run({"timetagger1":cutfile}, group='quTAG') #Runs the time tagging analysis and generates histograms
    histogram=result[ch_sel] #Selects the intended output from ETA, in this case it returns a 2-d array. The y axis for all ToF histograms. X axis must be recreated seperatly
    TOF_anal_time =  t.time() - TOF_anal_start

    print(f"Number of histograms produced: {histogram.shape}")
    
    return result, histogram

def save_data(file,x,y):
    #Saves a single pixel (x,y) to be used for trouble shooting and diagnosing
    file=Path(file)
    DATAFOLDER = f'analyzed data({base_binsize}ps bins)'
    
    if not os.path.exists(file.parent.joinpath(DATAFOLDER)):
        os.makedirs(file.parent.joinpath(DATAFOLDER))
    
    savepath = str(file.parent.joinpath(DATAFOLDER, file.stem) )+ ".txt"
    np.savetxt(savepath,np.transpose([x,y]))


"""Set Parameters for analysis and plotting"""
recipe = "C:/Users/staff/Documents/Lidar LF/ETA_recipes/quTAG_Microscope_0.3.eta" #ETA_recipe file

#.timeres file to analysed
file = 'C:/Users/staff/Documents/Microscope LF/data/220818/test3_scanning_code_APE_Xlim_[-0.05, 0.0]_100_Xres_10_Yres_0.1amp_2_794nm_det4_bias_12.65uA_12kCts_220818.timeres'

#Parameters for etabackend to generate histograms
ch_sel = 't1' #Selects a specific histogram
records_per_cut = 2e5 #Number of events to be used per evalution cycle in ETA, not important in this code
base_sync_delay = 0 #40000  #All events of the sync channel is delayed by 40000 ps (not necessary)
base_binsize = 16 #Histogram binsize in ps
base_bins = 780 #12500 #Number of bins in the histogram: bins*binsize should equal 1/f where f is the repition rate of the laser in use
base_delay = 0

#Dimensions of the scan
base_Xres = 100 # number of steps in the scan steps == resolution
base_Yres = 10

result, histogram = ToF_analysis(file, recipe, ch_sel,
                                                          bins = base_bins, binsize=base_binsize,
                                                          dimX=base_Xres, dimY=base_Yres, sync_delay = base_sync_delay)
"""
time = np.arange(0, base_bins)*base_binsize
for i in range(Xres):
    for j in range(Yres):
        ax, fig = plt.subplots()
        ax.plot(time, histogram[i][j])
        savepath = 
        plt.savefig()
"""
