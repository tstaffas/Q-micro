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

def eta_counter(recipe_file, timetag_file, **kwargs):
    #Load the recipe from seperate ETA file
    with open(recipe_file, 'r') as filehandle:
        recipe_obj = json.load(filehandle)

    eta_engine = etabackend.eta.ETA()
    eta_engine.load_recipe(recipe_obj)

    #Set parameters in the recipe
    for arg in kwargs:
        eta_engine.recipe.set_parameter(arg, str(kwargs[arg]))

    eta_engine.load_recipe()
    #print("Starting ETA analysis \n\n")
    
    file = Path(timetag_file)
    cutfile = eta_engine.clips(filename=file, format=1)
    result = eta_engine.run({"timetagger1" : cutfile}, group='qutag')  # Runs the time tagging analysis and generates histograms

    signals = {100 : 'c100', 101 : 'c101', 102 : 'c102', 103 : 'c103',
               0 : 'c0', 1 : 'c1', 2 : 'c2', 3 : 'c3', 4 : 'c4',
               5 : 'c5' , 6 : 'c6', 7 : 'c7', 8 : 'c8'}
    
    print(f"Signals : counts")
    for s in signals:
        print(f"{s} : {result[signals[s]]}")


recipe = 'signal_counter.eta'
file = 'Data/Testing_ch1_negative_pulse_ch2_positive_pulse.timeres'  # not changed
eta_counter(recipe, file)

"""
test = 1
if test == 1:
    print("\nORIGINAL TIMERES FILE  (ch: -1, 2)")
    recipe = 'signal_counter.eta'
    file = 'Data/Testing_ch1_negative_pulse_ch2_positive_pulse.timeres'  # not changed

    #2 : 213119
    #3 : 0   (note: this is because we still have -1 as channel nr)
    eta_counter(recipe, file)

    print("_____________________________________"
          "\nALTERED TIMERES FILE  (ch: 101, 2)")
    recipe = 'signal_counter.eta'
    file = 'Data/changed_Testing_ch1_negative_pulse_ch2_positive_pulse.timeres'  # changed  -1 --> 101
    #2 : 213119
    #3 : 213103
    eta_counter(recipe, file)

print("")
print("%%%%%%%%")
print("")
test = 2
if test == 2:
    # NOTE: HERE WE TRIED TO CONVERT EVEN THE POSITIVE CHANNELS (TO DOUBLE CHECK)
    print("\nORIGINAL TIMERES FILE   (channels:  1, 2, 3)")
    recipe = 'signal_counter.eta'
    file = 'Data/231030/ToF_terra_10MHz_det2_10.0ms_[2.1, 2.5, -3.2, -4.8]_100x100_231030.timeres'   # not changed
    eta_counter(recipe, file)

    print("_____________________________________"
          "\nALTERED TIMERES FILE    (channels:  1, 2, 3)")
    recipe = 'signal_counter.eta'
    file = 'Data/231030/changed_ToF_terra_10MHz_det2_10.0ms_[2.1, 2.5, -3.2, -4.8]_100x100_231030.timeres'   # not changed
    eta_counter(recipe, file)"""

print("\ndone!")
