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
from matplotlib.colors import LogNorm

import LIDAR_lib_01 as lidar  #Contains functions for 3D analysis
import intensity_map 

from skimage.io import imread, imshow
from skimage.color import rgb2gray
from skimage.transform import rescale
from scipy.signal import convolve2d

def ToF_histogram_offset(h,delay, binsize):
    delay_index = int(delay/binsize)
    return np.concatenate((h[delay_index:], h[0:delay_index]))
    
def ToF_analysis(timetag_file, recipe_file, ch_sel, **kwargs):
    load_start = t.time()
    #Load the recipe from seperate ETA file
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
    
    return histogram, START, load_time, TOF_anal_time


#--------------- Analysing the ToF histograms -----------
def analyse_3d(histogram, index_cutoff_lower, index_cutoff_upper, index_ref, x_deg, y_deg, time, method = 'peak', background = 6, delay = 0):
    METHODS = {'peak': lidar.peak_distance, 'gauss': lidar.gauss}
    anal = METHODS[method]
    print("Starting 3D analysis")
    d_data = {}  #used to store the distance data
    i_data = {}
    
    average_peak = 0  #some fun values to keep track of
    average_failed_peak = 0 #some fun values to keep track of
    
    F = 0   #Used to keep track of the number of failed pixels
    start = t.time() #Evaluate the time efficiency of the algorithms
    
    """
    Code block loops through all histograms. Removes background/internal reflections and calculates the distance to a reference value that must be measured separately (but is reused for all scans)
    """
    dimX = len(x_deg)
    dimY = len(y_deg)
    for i in range(0,dimY):
        print(i,"/",dimY)
        for j in range(0,dimX):
            h = histogram[i][j]
            #h = ToF_histogram_offset(h,delay, binsize)
            h[:index_cutoff_lower] = 0 #Cuts away the internal reflections, and is based on a background measurement. 
            h[index_cutoff_upper:] = 0
                
            peak = np.amax(h) #Identifies the target peak
            if peak > background:  #removes pixels with only noise, noise threshold can be modified                #d, _ = lidar.gauss(time,h,index_ref) #Gaussian algorithm
                #d, intensity = lidar.peak_distance(time,h, index_ref)#d = lidar.getDistance(index_ref, h, binsize = binsize)  #Peak finding Algorithm
                d, intensity, height = anal(time, h, index_ref)
                if d != np.NaN: #Gaussian algorithm can return np.NaN if unable to fit a curve to data, very unlikely after filtering away peaks with. It's a relic and might be obselete (but it's not hurting anyone)
                    x,y,z = lidar.XYZ(np.abs(d),x_deg[j],y_deg[i])
                    d_data[(x,y)] = z

                    #intensity = integral(h, height)                    
                    i_data[(x_deg[j],y_deg[i])] = intensity
                    #i_data[(y_deg[i], x_deg[j])] = intensity
                    
                average_peak += height
                
            else:
                i_data[(x_deg[j],y_deg[i])] = 0
                #i_data[(y_deg[i], x_deg[j])] = intensity
                
                F +=1
                average_failed_peak += peak
                
    stop = t.time()
    print("Failed pixels: ", F)
    print("Average peak: ", average_peak/(dimY*dimX - F))
    if F!=0:
        print("Average failed peak: ", average_failed_peak/F)

    print("3D analysis time: ", stop-start)
    return d_data, i_data



"""Set Parameters for analysis and plotting"""
recipe = "C:/Users/staff/Documents/Lidar LF/ETA_recipes/quTAG_LiDAR_1.2.eta" #ETA_recipe file

#.timeres file to analysed
file = 'C:/Users/staff/Documents/Lidar LF/Data/220614/bio_sample_790.8nm_40.0ms_1400cts_-17.85uA_[1.2, 1.2, -1.2, -1.2]_100x100_220614.timeres'
anal_method = "peak"

#Parameters for etabackend to generate histograms
base_binsize = 16 #Histogram binsize in ps
base_bins = 12500 #Number of bins in the histogram: bins*binsize should equal 1/f where f is the repition rate of the laser in use
ch_sel = 't1' #Selects a specific histogram
records_per_cut = 2e5 #Number of events to be used per evalution cycle in ETA, not important in this code
base_sync_delay = 0 #40000  #All events of the sync channel is delayed by 40000 ps (not necessary)

base_delay = 0

#Dimensions of the scan
base_dimX = 100 # number of steps in the scan steps == resolution
base_dimY = 100


time = (np.arange(0,base_bins)*base_binsize) #Recreate time axis

#----------------- Variables ---------------------
#Scanning variables
rect = [1.2, 1.2, -1.2, -1.2] #Voltage range of scan, linear to angle
x_deg, y_deg = lidar.angles(rect,base_dimX,base_dimY)

#Analysis parameter
time_ref_lower = 1800 #107500 #10500 #
index_cutoff_lower = int(time_ref_lower/base_binsize) #Removes the background noise. This value depends on the specifics of the setup and the delays. Must be optimised for new setups
index_ref = int(time_ref_lower-1500/base_binsize) #Time index of the mirrors position, used as origin when calculating 3D point clouds. Not at zero because the laser must first travel to the optical setup. Mus be measured seperatly

time_ref_upper = 5000 #107500 #10500 #
index_cutoff_upper = int(time_ref_upper/base_binsize) #Removes the background noise. This value depends on the specifics of the setup and the delays. Must be optimised for new setups
index_ref = int(time_ref_upper - 1500/base_binsize) #Time index of the mirrors position, used as origin when calculating 3D point clouds. Not at zero because the laser must first travel to the optical setup. Mus be measured seperatly

#Plotting parameters
coff = 4  #Removes outliers for plotting purposes. Simply to avoid squished plots
z_rot = 270 #Angle of wiev in 3D plot
x_rot = 20


histogram, START, load_time, TOF_anal_time = ToF_analysis(file, recipe, ch_sel,
                                                          bins = base_bins, binsize=base_binsize,
                                                          dimX=base_dimX, dimY=base_dimY, sync_delay = base_sync_delay)

d_data, i_data = analyse_3d(histogram, index_cutoff_lower, index_cutoff_upper, index_ref,
                            x_deg, y_deg, time,
                            method = anal_method,  background = 6, delay = base_delay)
file = Path(file)

##lidar.save_pixel_array(histogram, file, dimX, dimY, binsize) #To save some raw data for troubleshooting
#lidar.save_all_pixels(histogram, file, dimX, dimY, binsize)

print("Loading time: ", load_time)
print("TOF analysis time: ", TOF_anal_time)
print("Total Analysis time: ", t.time()-START)

#-------------------- Save code -------------
print("Saving Images")
coff = int(coff) # prevents the images from being to squished

kernel = 'identity'
i_matrix = intensity_map.intensity_matrix(i_data, 1e7, 10, intensity_map.KERNELS[kernel])
intensity_map.plot_heatmap(i_matrix)

#lidar.scatter(d_data, file, cutoff = coff, name = anal_method + "_Fit_", show = True)#, ylim = (300,600), xlim=(-200,200))#
#lidar.save_data(d_data, file, anal_method + '_')
print("Job Done!")


