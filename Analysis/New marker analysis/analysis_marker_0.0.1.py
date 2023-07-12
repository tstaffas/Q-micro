#------IMPORTS-----
#Packages for ETA backend
import json
import etabackend.eta #Available at: https://github.com/timetag/ETA, https://eta.readthedocs.io/en/latest/
import etabackend.tk as etatk

import os
import time as t
from pathlib import Path


from matplotlib import pyplot as plt
import numpy as np

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



recipe_file = 'C:/Users/staff/Downloads/microscope 0.0.7.eta'
timetag_file = 'C:/Users/staff/Documents/Microscope LF/data/230711/digit_8_sineAmp_(0.3)_sineFreq(10)_stepDim(_100)_stepAmp_(0.3)_date(230711)_time(12h04m).timeres'
timetag_file = 'C:/Users/staff/Documents/Microscope LF/data/230711/digit_8_sineAmp_(0.3)_sineFreq(1)_stepDim(_100)_stepAmp_(0.3)_date(230711)_time(11h26m).timeres'

#Settings:
dimX = 100
frequency = 1

bins = 100
binsize = int(1/(2*frequency*dimX)*1e12)


eta_engine = load_eta(recipe_file, binsize = binsize, bins = bins, dimX = dimX)
result = eta_analysis(timetag_file, eta_engine)

histogram = result['h2']

countrate = []

img = []

flip = True
for i in range(dimX):
    countrate.extend(histogram[i])
    
    if i%2 == 0 and flip:
        img.append(np.flip(histogram[i]))
        
    else:
        img.append(histogram[i])


#plt.plot(countrate)
#plt.show()


plt.imshow(img)
plt.show()
