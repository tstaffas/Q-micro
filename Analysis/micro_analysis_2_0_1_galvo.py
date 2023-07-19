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

import q_micro_lib_2_0_1_galvo as Q #Contains functions for image analysis and image construction for the quantum microscope

def ToF_analysis(timetag_file, recipe_file, ch_sel, ampY, ampX, yfreq, xfreq, S, **kwargs):
   
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
        yvaluelist.append(Q.yValueFunc(ampY, yfreq, realtime[i]))

    velocitylist = [] # create a list of velocities for each timestep (unit current/time)
    for i in range(len(time_axis)):
        velocitylist.append(Q.yVelocityFunc(ampY, yfreq, realtime[i]))

    velocitybinlist = [] # create a list of y-value contributions for each time-step. Calculated as y-value = velocity * base_binsize 
    for i in range(len(velocitylist)):
        velocitybinlist.append(velocitylist[i] * base_binsize)

    xvaluelist = [] # create a list of x-values for each timestep (unit current)
    for i in range(len(time_axis)):
        xvaluelist.append(Q.xValueFunc(S, realtime[i]))

    xvaluelist2 = [] # create a list of x-values for each timestep (unit current) based on a sinusfunction
    for i in range(len(time_axis)):
        xvaluelist2.append(Q.xValueFunc2(ampX, xfreq, realtime[i]))

    return countrate, time_axis, realtime, yvaluelist, velocitylist, velocitybinlist, xvaluelist, xvaluelist2

###----- Set Parameters for analysis and plotting -----###
#recipe = "/Users/mikaelschelin/Documents/QNP/Q-micro/ETA_recipe/T_microscope_double_0.0.1.eta" #ETA_recipe file new with code 101
recipe = "/Users/mikaelschelin/Documents/QNP/Q-micro/ETA_recipe/microscope 0.0.2.eta" #ETA_recipe file new with code 101

#file = '/Users/mikaelschelin/Documents/QNP/Q-micro/Data/20230713/digit_8_double_markers_sineAmp_(0.3)_sineFreq(1)_stepDim(_100)_stepAmp_(0.3)_date(230713)_time(16h46m37s).timeres'
file = '/Users/mikaelschelin/Documents/QNP/Q-micro/Data/20230713/digit_8_double_markers_sineAmp_(0.3)_sineFreq(1)_stepDim(_100)_stepAmp_(0.3)_date(230713)_time(16h46m37s).timeres'



###------ Set parameters from the scanning file --------###
dimX = 100 #Pixel dimensions
dimY = 100
#ampY = 0.09 #Standard setting 0.05. Unit ampere
ampY = 0.3 #unit voltage
yfreq = 1.0 * 1e-12 #standard setting 0.5 * 1e-12. Unit ps
resY = 1e8 #1e8 #Standard setting 1e10 ps = 10 ms. 1e8 = 0.1 ms. Lowest possible is 1 ps, which is the lowest possible integration time, however python list problems, need to partition to several count-lists if lower than 10e8 ps. 

#Settings for resonant scanning i x-direction
xfreq = 0.8 * 1e-12
ampX = 0.3 #0.09

###-------Set parameters for etabackend to generate histograms -------###
ch_sel = 'h2' #Selects a specific histogram
records_per_cut = 2e5 #Number of events to be used per evalution cycle in ETA, not important in this code
base_sync_delay = 0 #40000  #All events of the sync channel is delayed by 40000 ps (not necessary)

base_binsize = resY #int((1 / (2 * yfreq)) / dimY) 
ff = 1.2 #buffert timeline
base_bins = int(((dimX * (1 / (2 * yfreq))) / base_binsize) * ff) #Number of bins in the histogram. If basebin_size is 1e10 it should be 12 000

S = 1 / (2 * yfreq) # S is equal to half the period (T/2) in ps
Sbins = S / resY # Sbins is the number of bins per half period (per swipe up or swipe down). This must be constant
pixelAY = (2 * ampY) / dimY # pixelA is the total y-value (current) for each pixel. This must also be constant. E.g. if half a period goes from y value -0.05 to 0.05 = 0.1, then pixelA is 0.1/100 = 0.001

pixelAX = (2 * ampX) / dimX

countrate, time_axis, realtime, yvaluelist, velocitylist, velocitybinlist, xvaluelist, xvaluelist2 = ToF_analysis(file, recipe, ch_sel, ampY, ampX, yfreq, xfreq, S, bins = base_bins, binsize = base_binsize)

#countrate = countrate.flatten()

plt.figure()
plt.plot(countrate)
plt.show()
plt.savefig("countrate.png")

for i in range(1):
    offset = int((0.000 * i * 1e12) / base_binsize) #unit list index
    index_0 = int((dimX / base_binsize) * (1 / (2 * yfreq))) # for resY = 1e10, index_0 should be 10 000
    realtime = realtime[0:index_0]
    totallength = len(realtime)
    countrate_adj = countrate[offset:] # Adjusted countrate
    print(len(countrate_adj))
    countadjlength = len(countrate_adj)
    difflength = totallength - countadjlength
    print(difflength)
    if difflength > 0: 
        for i in range(difflength):
            countrate_adj.append(0)

    #Method 1. Create a speed adjusted pixel matrix, based on a generalized method for resonant scanning in y-direction and stepwise in x-direction. 
    #This method be generalized further independent of scanning patterns in x- and y-direction
    #imatrix = Q.createXYMatrix(dimX, dimY, pixelAY, ampY, xvaluelist, yvaluelist, countrate, time_axis) 

    #Method 2. Create a speed adjusted pixel matrix, based on a generalized method for resonant scanning in both x- and y-direction
    #imatrix = Q.createXYMatrix2(dimX, dimY, pixelAY, pixelAX, ampY, ampX, xvaluelist2, yvaluelist, countrate, time_axis)

    #Method 2b. Create a speed adjusted pixel matrix, based on a generalized method for sawtooth scanning i x-direction and resonant scanning in y-direction
    #imatrix = Q.createXYMatrix3(dimX, dimY, pixelAY, pixelAX, ampY, ampX, xvaluelist2, yvaluelist, countrate, time_axis)

    # Method 3. Create a speed-adjustment pixel matrix, place the right number of bins in each pixel given the swipe speed, based on resonant scanning in y-direction and stepwise in x-direction
    #imatrix = Q.createAdjustedMatrix(dimX, dimY, Sbins, pixelAY, velocitybinlist, countrate_adj) 

    # Method 4. Create a non speed adjusted pixel matrix, places an equal amount of bins in each pixel, based on resonant scanning in y-direction and stepwise in x-direction
    imatrix = Q.createEqualMatrix(dimX, dimY, Sbins, countrate_adj)

    # Method 5. Notice this is the original method that only works for resY = 1e10, where Sbins = dimY = 100. Thus, each bin is a pixel in the y-direction (100 bins = 100 pixels in y-direction)
    # Based on resonant scanning in y-direction and stepwise in x-direction
    #imatrix = Q.createOriginalImage(dimX, dimY, resY, Sbins, countrate)

    ##--- Set pixel high pass filter ----###
    threshold = 12000 #set threshold of pixel values

    #hPMatrix = Q.setHighPassFilter(imatrix, threshold, dimX, dimY)
    hPMatrix = np.array(imatrix) #Q.setHighPassFilter(imatrix, threshold, dimX, dimY)

    plt.figure()
    plt.imshow(hPMatrix, cmap='hot')
    plt.colorbar()
    plt.savefig("pixelimage_" + str(i) + ".png")
    plt.show()

# kernellist = ['blur', 'gauss33', 'gauss55', 'sharpen']

# filter_im = Q.convolver(hPMatrix, kernellist[2], 1)
# plt.imshow(filter_im, cmap='hot')
# plt.colorbar()
# plt.savefig("pixelimage_gaussian55.png")
# plt.show()

# edgematrix = Q.edge_detection(Q.convolver(hPMatrix, kernellist[2], 1) )
# plt.imshow(edgematrix, cmap='hot')
# plt.colorbar()
# plt.savefig("pixelimage_edge.png")
# plt.show()

# Q.fouriertransform(hPMatrix, "counts")
# Q.fouriertransform(filter_im, "counts_filter")
# Q.fouriertransform(edgematrix, "counts_edge")

###----code to write data-points to file----### 
#text_file=open('result.txt', 'a')
#for i in range(len(time_axis)):
#    text_file.write(str(time_axis[i]) + ' ' + str(time_ax_bins[i]) + ' ' + str(time_ax_bins[i]/1e9) + ' ' + str(time_ax_bins[i]/1e12) + ' ' + str(speedlist[i]) + ' ' + str(speedlist[i]*1e9) + ' ' + str(speedlist[i]*1e12) + ' ' + str(yvaluelist[i]) + ' ' + str(abs(yvaluelist[i])) + ' ' + str(velocitybinlist[i]) + ' ' + str(countrate[i]) + ' ' + str(abs(speedlist[i])) + ' ' + str(abs(velocitybinlist[i])) + '\n')
#text_file.close()


#######---- Improvement suggestions -----#######
# Remove possible artefacts due to limitations in image acquision and build up: 
# 1. Aliasing https://en.wikipedia.org/wiki/Aliasing
#   => anti-aliasing filter https://en.wikipedia.org/wiki/Anti-aliasing_filter
# 2. Interlacing https://en.wikipedia.org/wiki/Interlaced_video
#   => delacing techniques https://en.wikipedia.org/wiki/Deinterlacing
