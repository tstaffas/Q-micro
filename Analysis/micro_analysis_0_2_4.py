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
import sys

from matplotlib import pyplot as plt
import matplotlib.cm as cm

import q_micro_lib_0_2_4 as Q #Contains functions for image analysis and image construction for the quantum microscope

def ToF_analysis(timetag_file, recipe_file, ch_sel, amp, yfreq, **kwargs):
   
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

    #---File handling---
    file = Path(timetag_file)

    #------ETA PROCESSING-----
    """
    Code block loads the time-tagging data and runs the ETA script to genereate ToF histograms
    """
    print("Starting TOF analysis")
    cutfile = eta_engine.clips(file)
    result = eta_engine.run({"timetagger1":cutfile}, group='qutag') #Runs the time tagging analysis and generates histograms
    countrate = result[ch_sel] #Selects the intended output from ETA, in this case it returns a 2-d array. The y axis for all ToF histograms. X axis must be recreated seperatly
    
    time_axis = np.arange(0, base_bins) #the time-axis is actually time-steps. To get time, multiply with bin-size
    
    realtime = [] # create the real time axis in unit time (ps) 
    for i in range(len(time_axis)):
        realtime.append(time_axis[i] * base_binsize)

    yvaluelist = [] # create a list of y-values for each timestep (unit current)
    for i in range(len(time_axis)):
        yvaluelist.append(Q.yValueFunc(amp, yfreq, realtime[i]))

    velocitylist = [] # create a list of velocities for each timestep (unit current/time)
    for i in range(len(time_axis)):
        velocitylist.append(Q.yVelocityFunc(amp, yfreq, realtime[i]))

    velocitybinlist = [] # create a list of y-value contributions for each time-step. Calculated as y-value = velocity * base_binsize 
    for i in range(len(velocitylist)):
        velocitybinlist.append(velocitylist[i] * base_binsize)


    return countrate, time_axis, realtime, yvaluelist, velocitylist, velocitybinlist

###----- Set Parameters for analysis and plotting -----###
recipe = "/Users/mikaelschelin/desktop/Docs/Q-micro-main/imageprocessingcode/newcode/20221004/Countrate-qutag_micro.eta" #ETA_recipe file
# make sure correct channel in recipe! 

#.timeres file to be analysed
file = '/Users/mikaelschelin/desktop/Docs/Q-micro-main/imageprocessingcode/newcode/20221004/data_221116/number8_LV_0mA_50000counts_amp009v5_[100,100]_[x,y]_[-0.02, 0]_xlim_0.09_amp_0.5_yfreq__bias_-12.65uA_30kHz_Cts_221116.timeres'

###------ Set parameters from the scanning file --------###
dimX = 100
dimY = 100
amp = 0.09 #Standard setting 0.05. Unit ampere
yfreq = 0.5 * 1e-12 #standard setting 0.5 * 1e-12. Unit ps
resY = 1e8 #Standard setting 1e10 ps = 10 ms. 1e8 = 0.1 ms. Lowest possible is 1 ps, which is the lowest possible integration time, however python list problems, need to partition to several count-lists if lower than 10e8 ps. 

###-------Set parameters for etabackend to generate histograms -------###
ch_sel = 'h3' #Selects a specific histogram
records_per_cut = 2e5 #Number of events to be used per evalution cycle in ETA, not important in this code
base_sync_delay = 0 #40000  #All events of the sync channel is delayed by 40000 ps (not necessary)

base_binsize = resY #int((1 / (2 * yfreq)) / dimY) 
ff = 1.2 #buffert timeline
base_bins = int(((dimX * (1 / (2 * yfreq))) / base_binsize) * ff) #Number of bins in the histogram. If basebin_size is 1e10 it should be 12 000

S = 1 / (2 * yfreq) # S is equal to half the period (T/2) in ps
Sbins = S / resY # Sbins is the number of bins per half period (per swipe up or swipe down). This must be constant
pixelA = (2 * amp) / dimY # pixelA is the total y-value (current) for each pixel. This must also be constant. E.g. if half a period goes from y value -0.05 to 0.05 = 0.1, then pixelA is 0.1/100 = 0.001

countrate, time_axis, realtime, yvaluelist, velocitylist, velocitybinlist = ToF_analysis(file, recipe, ch_sel, amp, yfreq, bins = base_bins, binsize = base_binsize)

offset = int((0.040 * 1e12) / base_binsize) #unit list index
# Offset seems to vary depending of structure of image :(
# For the three lines image
    # Original algorithm not speed adjusted
        # yfreq = 0.5: resY 1e10 => 0.295
        # yfreq = 1.0: resY 1e10 => 0.150
        # yfreq = 2.0: resY 1e10 => 0.080
    # Speed adjusted algorithm
        # yfreq = 0.5: resY 1e8 => 0.292
        # yfreq = 0.5: resY 1e9 => 0.270
# For the digit 8 image
    # Speed adjusted algorithm
        # yfreq = 0.5: resY 1e8 => 0.040

index_0 = int((dimX / base_binsize) * (1 / (2 * yfreq))) # for resY = 1e10, index_0 should be 10 000
countrate = countrate[offset:index_0+offset] # Adjusted countrate
time_axis = time_axis[0:index_0]  # Adjusted time-axis

# Method 1. Create a speed-adjustment pixel matrix, place the right number of bins in each pixel given the swipe speed
imatrix = Q.createAdjustedMatrix(dimX, dimY, Sbins, pixelA, velocitybinlist, countrate) 

# Method 2. Create a non speed adjusted pixel matrix, places an equal amount of bins in each pixel 
#imatrix = Q.createEqualMatrix(dimX, dimY, Sbins, countrate)

# Method 3. Notice this is the original method that only works for resY = 1e10, where Sbins = dimY = 100. Thus, each bin is a pixel in the y-direction (100 bins = 100 pixels in y-direction)
#imatrix = Q.createOriginalImage(dimX, dimY, resY, Sbins, countrate)

###--- Set pixel high pass filter ----###
threshold = 20000 #set threshold of pixel values

hPMatrix = Q.setHighPassFilter(imatrix, threshold, dimX, dimY) # create image matrix with threshold

plt.imshow(hPMatrix, cmap='hot') #print heatmap image of threshold pixel matrix
plt.colorbar()
plt.savefig("pixelimage.png")
plt.show()

kernellist = ['blur', 'gauss33', 'gauss55', 'sharpen'] #various filters in the library

filter_im = Q.convolver(hPMatrix, kernellist[2], 1) #print heatmap image with a filter
plt.imshow(filter_im, cmap='hot')
plt.colorbar()
plt.savefig("pixelimage_gaussian55.png")
plt.show()

edgematrix = Q.edge_detection(Q.convolver(hPMatrix, kernellist[2], 1)) # print heatmap image with edge detection
plt.imshow(edgematrix, cmap='hot')
plt.colorbar()
plt.savefig("pixelimage_edge.png")
plt.show()

Q.fouriertransform(hPMatrix, "counts") # print frequency space of pixel matrix with threshold
Q.fouriertransform(filter_im, "counts_filter") # print frequency space of pixel matrix with filter
Q.fouriertransform(edgematrix, "counts_edge") # print frequency space of pixel matrix with edge detection

###----code to write data-points to file----### 
#text_file=open('result.txt', 'a')
#for i in range(len(time_axis)):
#    text_file.write(str(time_axis[i]) + ' ' + str(time_ax_bins[i]) + ' ' + str(time_ax_bins[i]/1e9) + ' ' + str(time_ax_bins[i]/1e12) + ' ' + str(speedlist[i]) + ' ' + str(speedlist[i]*1e9) + ' ' + str(speedlist[i]*1e12) + ' ' + str(yvaluelist[i]) + ' ' + str(abs(yvaluelist[i])) + ' ' + str(velocitybinlist[i]) + ' ' + str(countrate[i]) + ' ' + str(abs(speedlist[i])) + ' ' + str(abs(velocitybinlist[i])) + '\n')
#text_file.close()

#######---- Improvement suggestions -----#######
# Remove possible artefacts due to limitations in image acquisition and build up: 
# 1. Aliasing https://en.wikipedia.org/wiki/Aliasing
#   => anti-aliasing filter https://en.wikipedia.org/wiki/Anti-aliasing_filter
# 2. Interlacing https://en.wikipedia.org/wiki/Interlaced_video
#   => delacing techniques https://en.wikipedia.org/wiki/Deinterlacing
