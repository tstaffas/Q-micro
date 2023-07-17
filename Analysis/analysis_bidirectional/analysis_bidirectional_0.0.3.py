#------IMPORTS-----
#Packages for ETA backend
import json
import etabackend.eta #Available at: https://github.com/timetag/ETA, https://eta.readthedocs.io/en/latest/
import etabackend.tk as etatk

import os
import time as t
from pathlib import Path


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

def countrate_analysis(countrate_matrix):
    img_matrix = []

    for i in range(dimX):
        row = countrate_matrix[i]
        flipped_row = row.copy()
        flipped_row= np.flip(flipped_row)

        row += flipped_row
        
        row = row[0:100]
        img_matrix.append(row)

    return img_matrix

def eta_analysis(file, eta_engine):
    print('Starting ETA analysis')
    cut=eta_engine.clips(Path(file))
    result= eta_engine.run({"timetagger1":cut}, group='qutag')
    print('Finished ETA analysis')
    
    return result


def ETA_segmented_analysis(timetag_file, ch_sel, eta_engine):
    print("Starting Analysis")
    #Result image
    
    #------ETA PROCESSING-----
    pos = 0
    context = None
    run_flag = True

    img = []
    countrate = []

    pst = 0
    while run_flag:
        file_clips = eta_engine.clips(Path(timetag_file), seek_event=pos)
        result, context = eta_engine.run({"timetagger1": file_clips}, resume_task=context,
                                        return_task=True, group='qutag', max_autofeed=1)
        
        if result['timetagger1'].get_pos() == pos:
            # No new elements left
            run_flag = False
            break
        
        pos = result['timetagger1'].get_pos()


        X = result["X"]
        #print(X)
        row = result[ch_sel]#[result['X']]
        
        countrate+= list(row)
        flipped_row = row.copy()
        flipped_row= np.flip(flipped_row)
        
        row += flipped_row
        row = row[0:int(bins/2)]
        img.append(list(row))

        
                   
    print("All elements processed.\nAnalysis Finished")
    return countrate, img




eta_recipe = 'C:/Users/staff/Documents/Microscope LF/microscope bidirectional segments 0.0.3.eta'
timetag_file = 'C:/Users/staff/Documents/Microscope LF/data/230717/higher_power_multi_trigger_digit_8_double_marker_sineFreq(100)_sineAmp(0.3)_stepAmp(0.3)_stepDim(100)_date(230717)_time(14h02m31s).timeres'

#Settings:
dimX = 100
frequency = 100

bins = 200
binsize = int(1/(frequency*bins)*1e12)

#####
eta_engine = load_eta(eta_recipe, bins = bins, binsize = binsize)

countrate, img = ETA_segmented_analysis(timetag_file, 'h2', eta_engine)

fig, ax = plt.subplots()
ax.imshow(img, cmap = 'hot')
plt.show()
