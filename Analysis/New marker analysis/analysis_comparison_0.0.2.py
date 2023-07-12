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



def eta_analysis(file, eta_engine):
    print('Starting ETA analysis')
    cut=eta_engine.clips(Path(file))
    result= eta_engine.run({"timetagger1":cut}, group='qutag')
    print('Finished ETA analysis')
    
    return result



no_markers_recipe = 'C:/Users/staff/Downloads/microscope 0.0.2.eta'
markers_recipe = 'C:/Users/staff/Downloads/microscope 0.0.9.eta'


timetag_file = 'C:/Users/staff/Documents/Microscope LF/data/230711/digit_8_sineAmp_(0.3)_sineFreq(10)_stepDim(_100)_stepAmp_(0.3)_date(230711)_time(12h04m).timeres'
#timetag_file = 'C:/Users/staff/Documents/Microscope LF/data/230711/digit_8_sineAmp_(0.3)_sineFreq(1)_stepDim(_100)_stepAmp_(0.3)_date(230711)_time(11h26m).timeres'

#Settings:
dimX = 100
frequency = 10

bins = 100*100
binsize = int(1/(2*frequency*dimX)*1e12)
x = np.arange(0,bins)

marker_engine = load_eta(markers_recipe, binsize = binsize, bins = 100, dimX = dimX)
no_marker_engine = load_eta(no_markers_recipe, binsize = binsize, bins = 1e4)

marker_result = eta_analysis(timetag_file, marker_engine)
no_marker_result = eta_analysis(timetag_file, no_marker_engine)


no_marker_countrate = no_marker_result['h2']

marker_countrate = []
padding = 0
for i in range(dimX):
    line = [0]*(padding) + list(marker_result['h2'][i])[padding:]
    marker_countrate.extend(line)

marker_countrate = np.array(marker_countrate)


#Start plotting
fig, ax = plt.subplots()
line_1, = ax.plot(x, no_marker_countrate, label = 'no markers')
line_2, = ax.plot(x, marker_countrate, label = 'markers')
ax.legend()


# adjust the main plot to make room for the sliders
fig.subplots_adjust(left=0.25, bottom=0.25)

# Make a horizontal slider to control the offset.
ax_offset = fig.add_axes([0.25, 0.1, 0.65, 0.03])
x_slider = Slider(
    ax=ax_offset,
    label='x',
    valmin=0,
    valmax=150,
    valinit=0,
)

x_slider.on_changed(update)

# Create a `matplotlib.widgets.Button` to reset the sliders to initial values.
resetax = fig.add_axes([0.8, 0.025, 0.1, 0.04])
button = Button(resetax, 'Reset', hovercolor='0.975')
button.on_clicked(reset)

plt.show()
"""
img_marker = []
img_no_marker = []

flip = False
for i in range(1,dimX+1):
    if i%2 == 0 and flip:
        img_no_marker.append(np.flip(no_marker_result['h2'][(i-1)*dimX: i*dimX]))
    else:
        img_no_marker.append(no_marker_result['h2'][(i-1)*dimX: i*dimX])
        

    if i%2 == 0 and flip:
        img_marker.append(np.flip(marker_result['h2'][i-1]))
    
    else:
        img_marker.append(marker_result['h2'][i-1])

"""
