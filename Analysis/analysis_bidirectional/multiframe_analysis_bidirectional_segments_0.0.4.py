#------IMPORTS-----
#Packages for ETA backend
#import json
#import etabackend.eta   # Available at: https://github.com/timetag/ETA, https://eta.readthedocs.io/en/latest/
#from pathlib import Path
from matplotlib import pyplot as plt
import numpy as np
import multiframe_library_bidirectional_segments as Q
import os


# TODO: USE BINSIZE IN SPEED-ADJUSTED MATRIX (if not already used)???


# ------------ PARAMETERS AND CONSTANTS --------------
eta_recipe = 'multiframe_recipe_bidirectional_segments_0.0.4.eta'        # 'microscope_bidirectional_segments_0.0.3.eta'

folder = "Data/230828/"         # Note: this is used to find the timeres file --> WRITE in your data folder location
clue = "digit_6"                   # Note: this is used to help find the correct timeres file when only given frequency (ex: 'higher_power', 'digit_8', '13h44m23s')
#    ^ex. for data in "230717": {"digit_8", "low", "high", "digit_6"}

timetag_file = None             # Note: let this be None if you want to use "clue" and "folder" to automatically find your file based on frequency
#timetag_file = 'Data/230717/higher_power_multi_trigger_digit_8_double_marker_sineFreq(100)_sineAmp(0.3)_stepAmp(0.3)_stepDim(100)_date(230717)_time(14h02m31s).timeres'
#timetag_file = 'digit_6_sineFreq(10)_numFrames(4)_sineAmp(0.3)_stepAmp(0.3)_stepDim(100)_date(230828)_time(09h34m06s).timeres'

# Scan parameters:
nr_frames = 4
freq = 10                      # {1, 4, 10, 20, 30, 50, 100, 100}   # note: 30 is missing 6 rows  # FIXME so it works if we don't have all dimX rows or dim Y pixels
ampX = 0.3                      # --> step values between -0.3 and 0.3
ampY = 0.3                      # --> sine values between -0.3 and 0.3
dimX = 100                      # how many (stepwise) steps we take in scan
bins = 20000                    # how many bins/containers we get back for one period   #20000 is good --> 10k per row
# TODO: Test -> bins=2*dimY. It should give the same image as non-speed adjusted image. We want to try to have one bin per pixel. We multiply by two since we have two sweeps which is combined.
ch_sel = "h2"

# Options:
use_flip = True                # flip every other sweep (1 sweep = half period) # NOTE from Julia: I strongly think that we should NOT flip
noise_tolerance = 0.09  # 0.05    # scale 0-1, lower bound of values that are considered noise (ex. 0.09 = 9% lowest values are noise)

# NOTE: BELOW MIGHT NOT BE OF USE FOR SIMPLE ANALYSIS
#use_blur = True                 # blur final image
# Noise & Binary mask filter:
#use_noise_filter = True           #
#noise_thresh = 0  # 10            # absolute value, used for high and low pass filters  TODO: depreciated. maybe use or maybe remove
#noise_saturation = 0.7            # scale 0-1, factor to dampen noise intensity with binary mask (useful after blur)  (ex. 0 = no noise, 0.3= 30% noise intensity)
# Transforms:
#kernel_list = ['blur', 'gauss33', 'gauss55', 'sharpen']  # micke uses 'gauss55'
#trans_iter = 1
#ker = 'gauss55'

# ------------ RELATIONSHIPS ------------

dimY = int(round(dimX*(ampY/ampX)))     # How many pixels we want to use TODO: Get new data (where ampX != ampY) and test this relationship!
#dimY = dimX                            # Note: if ampX == ampY --> dimY = dimX gives square pixels. (but if ampX != ampY we would get a stretching distortion)
# TODO: test to set dimY to our sine resolution in scan code (to match exact theoretical movement)  -> 256 or 512

freq_ps = freq * 1e-12                  # frequency scaled to unit picoseconds (ps)
period_ps = 1/freq_ps                   # period in unit picoseconds (ps)
binsize = int(round(period_ps/bins))    # how much time (in ps) each histogram bin is integrated over (=width of bins). Note that the current recipe returns "bins" values per period.
print("bins =", bins, " ,  binsize =", binsize*10e-12, "seconds")

# NOTE: Below is a dictionary with all the parameters defined above. This way we can sent a dict with full access instead of individual arguments
const = {
    "eta_recipe"       : eta_recipe,
    "timetag_file"     : timetag_file,
    "clue"             : clue,
    "folder"           : folder,
    "nr_frames"        : nr_frames,
    "freq"             : freq,
    "ampX"             : ampX,
    "ampY"             : ampY,
    "dimX"             : dimX,
    "bins"             : bins,
    "ch_sel"           : ch_sel,
    "use_flip"         : use_flip,
    "noise_tolerance": noise_tolerance,
    #"use_blur"         : use_blur,
    #"use_noise_filter" : use_noise_filter,
    #"noise_thresh"     : noise_thresh,
    #"noise_saturation" : noise_saturation,
    #"kernel_list"      : kernel_list,
    #"trans_iter"       : trans_iter,
    #"ker"              : ker,
    "dimY"             : dimY,
    "freq_ps"          : freq_ps,
    "period_ps"        : period_ps,
    "binsize"          : binsize,
    }


# --------- GET DATA AND HISTOGRAMS------------

# quick version of "ad infinitum" code where we generate one image/frame at a time from ETA
if __name__ == "__main__":

    # --- GET TIMETAG FILE NAME, unless manually provided ---
    if timetag_file is None:
        timetag_file = Q.File.get_timres_name(folder, freq, clue=clue)
        const["timetag_file"] = timetag_file

    # --- PROVIDE WHICH MAIN FOLDER WE SAVE ANY ANALYSIS TO FOR THE USED ETA FILE (ex. images, raw data files, etc.)
    st = timetag_file.find("date(")
    fin = timetag_file.find(".timeres")
    const["save_location"] = f"Analysis/({str(freq)}Hz)_{timetag_file[st:fin]}"   # This is the folder name for the folder where data, images, and anything else saved from analysis will be saved
    #       FOR EXAMPLE: const["save_location"] = Analysis/(100Hz)_date(230717)_time(14h02m31s)

    # --- EXTRACT AND ANALYZE DATA ---
    Q.MultiFrame.eta_segmented_analysis_multiframe(const=const, return_full=False)   # note: all params we need are sent in with a dictionary. makes code cleaner

    """  # --------
    countrate_raw, countrate_filtered, countrate_matrix, img_no_flip, img_with_flip, raw_adjusted_matrix, filtered_adjusted_matrix, flipped_adjusted_matrix, const  \
        = Q.MultiFrame.eta_segmented_analysis_multiframe(const=const, return_full=True)   # note: all params in a dict that is sent in. makes code cleaner
    
    # NOTE:
    #  In this script we do return from ETA analysis to further perform tests, but all the plotting and filters below are temporarily extensive.
    #  We should be able to all image processing in the ETA analysis method when we know what we want
    # --------

    # --- MISC ---
    #mid_val = max(np.array(img_no_flip).flatten())/2    # used as approx mid-value for intensity

    # define which countrate list we want to use
    #if use_noise_filter:
    #    full_countrate = countrate_filtered
    #    J_adjusted_matrix = filtered_adjusted_matrix
    #else:
    #    full_countrate = countrate_raw
    #    J_adjusted_matrix = raw_adjusted_matrix

    # ------ FILTERS -------
    #img_no_flip_low_filter = Q.Process.low_filter(matrix=np.array(img_no_flip), lower_thresh=const["noise"], lower_val=0)
    #Q.Plot.subplots_compare_flip(dimX, dimY, raw_adjusted_matrix, filtered_adjusted_matrix,  titles=["No Filter", "Filter"], fig_title="filtering_speed") # Compares FILTERING and no filtering on non speed adjusted image

    # --- COUNTRATE ---
    #Q.Plot.full_countrate(countrate_raw)   # countrate figure we're used to seeing
    #Q.Plot.compare_noise_full_countrate(countrate_raw, countrate_filtered)   # Zoom in on an area to see that noise is removed in deadzones
    #Q.Plot.histo_distribution(full_countrate, "full countrate")  # Histogram of pixel values in non-speed adjusted image --> shows that there is a lot of noise

    # --- HISTOGRAM ---
    # Histogram of pixel values in non-speed adjusted image --> shows that there is a lot of noise
    #Q.Plot.histo_distribution(img_no_flip, "raw image no flip")
    #Q.Plot.histo_distribution(img_no_flip_low_filter, "filtered image no flip")

    # --- FLIPPING ---
    #Q.Plot.plot_flip_diff(const)   # Full comparison: flipping vs no flipping
    #Q.Plot.subplots_compare_flip(dimX, dimY, raw_adjusted_matrix, flipped_adjusted_matrix, titles=["No Flip", "Flip"], fig_title="flipping_speed")  # Compares FLIPPING vs no flipping, on non speed adjusted image

    #This will show an image where high and low value functions show how they perform
    # Note: this is interesting to visualize noise
    #_, _, _ = Q.Plot.test_value_filters(matrix=raw_adjusted_matrix, lower_thresh=const["noise"], upper_thresh=const["noise"], upper_val=mid_val, noise=const["noise"], m=mid_val, num="no flip")
    #_, _, _ = Q.Plot.test_value_filters(matrix=flipped_adjusted_matrix, lower_thresh=const["noise"], upper_thresh=const["noise"], upper_val=mid_val, noise=const["noise"], m=mid_val, num="flipped")

    # --- MASS SUBPLOTS ---
    #Q.Plot.refine_image_subplots(filtered_adjusted_matrix, raw_adjusted_matrix, img_no_flip, img_with_flip, const)
    #Q.Plot.filter_vs_raw_subplots(filtered_adjusted_matrix, raw_adjusted_matrix, const, const["noise"])  # TODO: save and retrieve noise another way

    # --- SPEED ADJUSTMENT ---
    # Note: Visual aid to explain what method "get_t_of_y" does.  # res parameter is lower just here for the plot
    #Q.Plot.draw_time_for_each_pixel(res=20, ampY=ampY, frequency=freq_ps)
    # Note the below two are already shown in the ETA analysis code
    #Q.Plot.image_heatmap(np.array(raw_adjusted_matrix), title="Raw speed adjusted", fig_title="Raw speed adjusted matrix 1")
    #Q.Plot.image_heatmap(np.array(J_adjusted_matrix), title="Speed adjusted", fig_title="Raw speed adjusted matrix 2")
    
    plt.show()

    """

# --------------------------

#
"""
#Q.Process.final_transforms_and_plots(matrix=J_adjusted_matrix, name='blur', kernel='blur', iter=trans_iter, thresh=noise)
#Q.Process.final_transforms_and_plots(matrix=J_adjusted_matrix, name='gauss33', kernel='gauss33', iter=trans_iter, thresh=noise)
#Q.Process.final_transforms_and_plots(matrix=J_adjusted_matrix, name='gauss55', kernel='gauss55', iter=trans_iter, thresh=noise)
#Q.Process.final_transforms_and_plots(matrix=J_adjusted_matrix, name='sharpen', kernel='sharpen', iter=trans_iter, thresh=noise)


# Previous matrix methods:
#   Kept our old version in lib just in case we wanted it --> velocity_bin_list = Q.Function.get_scan_bin_lists(ampY, freq_ps, bins, binsize) # Previously used base_bins and base_binsize

# PREVIOUS METHODS:
#i_matrix1 = Q.Construct.XYMatrix(dimX, dimY, pixelAY, ampY, xvaluelist, yvaluelist, countrate, time_axis)  # Method 1
#i_matrix3 = Q.Construct.AdjustedMatrix(dimX, dimY, Sbins, pixelAY, velocity_bin_list, countrate)  # Method 3
#i_matrix4 = Q.Construct.EqualMatrix(dimX, dimY, Sbins, countrate)   # Method 4

"""
