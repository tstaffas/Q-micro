#------IMPORTS-----
#Packages for ETA backend
import json
import etabackend.eta #Available at: https://github.com/timetag/ETA, https://eta.readthedocs.io/en/latest/

#Packages used for analysis
import numpy as np
from pathlib import Path
import time as t

from matplotlib import pyplot as plt
import sys

from q_micro_lib import *  #Contains functions for image analysis and image construction for the quantum microscope
    
def ToF_analysis(timetag_file, recipe_file, ch_sel, **kwargs): #Function for data acquisition for the microscope, generates a nested list of histograms, 10 000 with count data
    load_start = t.time()
    with open(recipe_file, 'r') as filehandle:
        recipe_obj = json.load(filehandle)

    eta_engine = etabackend.eta.ETA()
    eta_engine.load_recipe(recipe_obj)

    #Set parameters in the recipe
    for arg in kwargs:
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

    print(f"Number of histograms produced: {result['pixelnumber']+1}")
    
    return histogram, START, load_time, TOF_anal_time #Returns a nested list of 10 000 histograms with count data

#--------------- Analysing the ToF histograms -----------

def imageProcessing(histogram, index_cutoff, index_ref, time, method, background, delay): #Function for image analysis and processing, returning a nested dictionary with time-of-flight, intensity and height for each of the 10 000 histograms
    METHODS = {'peak': peak_metrics, 'gauss': gauss_metrics} #Add 'gauss': qlib.gauss add a curve fitting method to get a more smooth out position of ToF, intensity and height
    process = METHODS[method]
    xdim=np.shape(histogram)[0]
    ydim=np.shape(histogram)[1]
    zdim=np.shape(histogram)[2] #the len of the histograms for each mirror position 6250 bins

    resultdict = {} #resultdictionary, nested dictionary with ToF, intensity and peak value for each histogram

    print("Starting image processing")

    total_peak = 0  
    total_failed_peak = 0 
    F = 0   #failed pixels
    start = t.time() #Evaluate the time efficiency of the algorithms
    
    """
    Code block loops through all histograms. Removes background/internal reflections and calculates the distance to a reference value that must be measured separately (but is reused for all scans)
    """
    for i in range(ydim): #If scanning dimensions are not square this might need to change
        print(i,"/",ydim)
        for j in range(xdim):
            h = histogram[i][j] #histogram for each mirror position
            h[:index_cutoff] = 0 #Cuts away the internal reflections, background_cutoff is assigned in ETA frontend and is based on a background measurement. 
            key=(i,j)
            peak = np.amax(h) #Identifies the target peak
            if peak > background:  #removes pixels with only noise, noise threshold can be modified 
                tof, intensity, height = process(time, h, index_ref)
                value={'ToF': tof, 'intensity': intensity, 'height': height}
                total_peak += height  
            else:
                value={'ToF': 0, 'intensity': 0, 'height': 0}
                F +=1
                total_failed_peak += peak
            
            resultdict[key] = value
                
    stop = t.time()

    print("Failed pixels: ", F)
    print("Average peak: ", total_peak/(xdim*ydim - F))
    if F!=0:
        print("Average failed peak: ", total_failed_peak/F)

    print("image processing time: ", stop-start)
    return resultdict

####THE PROGRAM STARTS HERE######

#ETA_recipe file
recipe = "/Users/mikaelschelin/Documents/Projects/Q-micro-main/quTAG_LiDAR_1.2.eta" 
#Data file to be analyzed
file = '/Users/mikaelschelin/Documents/Projects/Q-micro-main/TerracottaMan_10ms_10MHz_0.45MHzCts_16.5uA_[8,8,-8,-8]_100x100_210522.timeres'

#Analysis method to be used for each count histogram
analysis_method = "peak" # peak method use the count histogram as it is and locates the max count value and its time position and calculate the ToF and intensity
# #gauss method fits a curve to the 

####Set instrument specific parameters for analysis - calibrate instrument to acquire settings####

#Parameters for etabackend to generate histograms
background = 6 #background noise, analyse histograms to set this parameter 
base_binsize = 16 #Histogram binsize in ps
base_bins = 6250 #Number of bins in the histogram: bins*binsize should equal 1/f where f is the repition rate of the laser in use
ch_sel = 't1' #Selects a specific histogram
records_per_cut = 2e5 #Number of events to be used per evalution cycle in ETA, not important in this code
base_sync_delay = 0 #40000  #All events of the sync channel is delayed by 40000 ps (not necessary)
base_delay = 0 

#Dimensions of the scan
base_dimX = 100 # number of steps in the scan steps == resolution
base_dimY = 100

time = (np.arange(0,base_bins)*base_binsize) #Recreate time axis

#Variables
time_ref = 72500 #Instrument specific to be set
index_cutoff = int(time_ref/base_binsize) #Removes the background noise. This value depends on the specifics of the setup and the delays. Must be optimised for new setups
index_ref = int((time_ref)/base_binsize) #Time index of the mirrors position, used as origin when calculating 3D point clouds. Not at zero because the laser must first travel to the optical setup. Must be measured seperatly

#Run the functions
histogram, START, load_time, TOF_anal_time = ToF_analysis(file, recipe, ch_sel, bins = base_bins, binsize=base_binsize, dimX=base_dimX, dimY=base_dimY, sync_delay = base_sync_delay)
resultdict = imageProcessing(histogram, index_cutoff, index_ref, time, analysis_method, background, delay = base_delay)

print("Loading time: ", load_time)
print("TOF analysis time: ", TOF_anal_time)
print("Total Analysis time: ", t.time()-START)

#-------------------- Generate images and save data to file -------------

#create and save resultfile of all 10 000 histograms with metrics (ToF, intensity, height) for each histogram per row
text_file=open('resultfile_metrics_per_histogram.txt', 'a')
for p in resultdict:
    text_file.write(str(p[0])+' '+str(p[1])+' '+str(resultdict[p]['ToF'])+' '+str(resultdict[p]['intensity'])+' '+str(resultdict[p]['height'])+'\n')
text_file.close()

kernellist = ['identity', 'blur', 'gauss33', 'gauss55', 'sharpen'] #Choose filter for image processing
metriclist = ['ToF', 'intensity', 'height'] #Choose metric for image construction: ToF, Intensity, Height
iterlist = [1] #, 3, 5, 10] #Filtering iterations

for i in range(len(metriclist)):
    metric_matrix, norm_metric_matrix, metric = i_matrix(resultdict, metriclist[i])
    edge_matrix = edge_detection(norm_metric_matrix)
    plot_heatmap(metric_matrix, metric, "nofilter", "values", "noiter")
    plot_heatmap(norm_metric_matrix, metric, "nofilter", "norm", "noiter")
    plot_heatmap(edge_matrix, metric, "edge", "norm", "noiter")
    fouriertransform(norm_metric_matrix, metriclist[i])

    for j in range(len(kernellist)):
        for m in range(len(iterlist)):
            filter_im = convolver(norm_metric_matrix, kernellist[j], iterlist[m]) 
            plot_heatmap(filter_im, metric, kernellist[j], "norm", iterlist[m])


print("Job Done!")
