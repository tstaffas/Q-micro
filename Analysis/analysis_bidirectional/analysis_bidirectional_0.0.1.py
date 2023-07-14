#------IMPORTS-----
#Packages for ETA backend
import json
import etabackend.eta #Available at: https://github.com/timetag/ETA, https://eta.readthedocs.io/en/latest/
import etabackend.tk as etatk

import os
import time as t
from pathlib import Path

import sys


from matplotlib import pyplot as plt
from matplotlib.widgets import Slider, Button
import numpy as np


# The function to be called anytime a slider's value changes
def update(val):
    line_2.set_xdata(x + x_slider.val)
    fig.canvas.draw_idle()

def reset(event):
    x_slider.reset()
    
    
#------- ETA analysis ----------
def load_eta(recipe, **kwargs):
    print('Loading ETA')
    with open(recipe, 'r') as filehandle:
        recipe_obj = json.load(filehandle)

    eta_engine = etabackend.eta.ETA()
    eta_engine.load_recipe(recipe_obj)

    #Set parameters in the recipe
    for arg in kwargs:
        eta_engine.recipe.set_parameter(arg, str(kwargs[arg]))

    
    eta_engine.load_recipe()

    return eta_engine



def eta_analysis(file, eta_engine):
    print('Starting ETA analysis')
    cut=eta_engine.clips(Path(file))
    result= eta_engine.run({"timetagger1":cut}, group='qutag')
    print('Finished ETA analysis')
    
    return result

#Add files: 

eta_recipe = "/Users/mikaelschelin/Documents/QNP/Q-micro/Code/bidirectional/analysis_bidirectional/microscope_bidirectional_0.0.1.eta" #ETA_recipe file new double markers

timetag_file = '/Users/mikaelschelin/Documents/QNP/Q-micro/Data/20230713/digit_8_double_markers_sineAmp_(0.3)_sineFreq(1)_stepDim(_100)_stepAmp_(0.3)_date(230713)_time(16h46m37s).timeres'

#Settings:
dimX = 100
frequency = 10 #in seconds
ch_sel = 'h2'


bins = 200
binsize = int(1/(frequency*dimX)*1e12) #In picoseconds


#Run program:

eta_engine = load_eta(eta_recipe, bins = bins, binsize = binsize)
result = eta_analysis(timetag_file, eta_engine)

countmatrix = result[ch_sel] #This is a Nx2N matrix where N is dimX

part = []
beginlist = []
endlist = []
pixelmatrix = []

for i in range(dimX):
    beginlist = countmatrix[i].tolist()
    endlist = beginlist.copy()
    endlist.reverse()
    for j in range(dimX):
        part.append(beginlist[j] + endlist[j])
    beginlist = []
    endlist = []
    pixelmatrix.append(part)
    part = []

pixelmatrix = np.array(pixelmatrix)

plt.figure()
plt.imshow(pixelmatrix, cmap='hot')
plt.colorbar()
plt.savefig("pixelimage_freq" + str(frequency) + ".png")
plt.show()

