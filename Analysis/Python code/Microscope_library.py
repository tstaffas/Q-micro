import os
from pathlib import Path
import numpy as np
from matplotlib import pyplot as plt
from PIL import Image  # for gif
# Packages for ETA backend
import json
import etabackend.eta  # Available at: https://github.com/timetag/ETA, https://eta.readthedocs.io/en/latest/
# Fun fact: line we scan is approx 150 micrometers wide

#..... UPDATED: 31 August 2023 .....#


# ----------- FILE HANDLING --------------
def get_timres_name(folder, num, freq, clue):
    """ searches for timeres filename (that fits params) in a folder and returns the name """
    for filename in os.listdir(folder):  # checks all files in given directory (where data should be)
        if clue in filename:
            # NOTE: "clue" helps us differentiate between two with the same frequency (e.g. clue="figure_8")
            if f"numFrames({num})" in filename:
                if f"sineFreq({freq})" in filename:
                    if ".timeres" in filename:
                        print("Using datafile:", filename)
                        return folder + filename    # this is our found timetag_file!
    print("No matching timeres file found! :(")
    exit()

def get_image_path(folder_name):
    # Checks if image folders exists in a directory, otherwise it creates it
    directory = Path(__file__).parent  # or "file_path.parent"  # Note: "Path(__file__)" is the path for this script/code file
    save_image_path = directory.joinpath(f'{folder_name}')
    if not os.path.exists(save_image_path):  # If folder does not exist, create it
        os.makedirs(save_image_path)
    return save_image_path


# ----------- MAIN ANALYSIS --------------
def eta_segmented_analysis_multiframe(const):
    """Extracts and processes one frame at a time. Due to this we have to do all image processing within the function"""

    # calculate sine times for speed adjustment (same for all rows, so we only do it once)
    t_from_even_y, y_even_spaced = get_t_of_y(res=const["dimY"], ampY=const["ampY"], frequency=const["freq_ps"])

    # --- LOAD RECIPE ---
    eta_engine = load_eta(const["eta_recipe"], bins=const["bins"], binsize=const["binsize"])  # NOTE: removed for test

    # ------ETA PROCESSING-----
    print("Starting Analysis")
    pos = 0           # internal ETA tracker (-> maybe tracks position in data list?)
    context = None    # tracks info about ETA logic, so we can extract and process data with breaks (i.e. in parts)
    image_nr = 0      # tracks which frame is being processed

    # step 1) repeat extraction and creations of frames while there are more frames to be created
    while image_nr < const["nr_frames"]:  # note: maybe alternative condition
        run_flag = True         # useful if runflag condition is used instead of "break"
        countrate_matrix = []   # to save data the same way it comes in (alternative to countrate list with more flexibility)
        row_nr = 0
        image_nr += 1           # note: image number starts at 1 and not 0 (i.e. not regular indexing)

        # step 2) Extracting rows until image is filled
        while run_flag:
            row_nr += 1
            row, pos, context, run_flag = get_row_from_eta(eta_engine, const["timetag_file"], pos, context, const["ch_sel"], run_flag)

            countrate_matrix.append(list(row))

            if row_nr == const["dimX"]:
                # Note: At this point we have filled one full image and want to move onto the next image
                print(f"Frame {image_nr}/{const['nr_frames']} complete!")
                break      # breaks out of inner while loop

        #  step 3) Flip every odd frame since we scan in different directions
        if image_nr % 2 == 0:  # note: indexing starts att 1 so odd frames are at even values of 'image_nr'
            countrate_matrix = np.flip(np.array(countrate_matrix))    # eller countrate_matrix.reversed()

        #  -------  PROCESS DATA INTO IMAGE: --------
        # create non adjusted image, compressing bins if needed
        non_speed_matrix = build_image_matrix(countrate_matrix, const["bins"], const["dimY"])  # raw images, flipping comparison

        # do speed adjustment on raw data
        adjusted_matrix = speed_adjusted_matrix_timebased(countrate_matrix, t_from_even_y, const)

        # create and save images:   # note: below two functions are needed to save the figs
        draw_image_heatmap(np.array(non_speed_matrix),       fig_title=f"non-speed adjusted - {const['freq']} Hz",  title=f"{const['freq']} Hz - non-speed adjusted - frame {image_nr}",  save_fig=True, save_loc=const["save_location"]+"/Original_Frames",  save_name=f"frame {image_nr}", showfig=False)
        draw_image_heatmap(np.array(adjusted_matrix), fig_title=f"speed adjusted - {const['freq']} Hz",      title=f"{const['freq']} Hz - speed adjusted - frame {image_nr}",      save_fig=True, save_loc=const["save_location"]+"/Speed_Frames",      save_name=f"frame {image_nr}", showfig=False)

    print("Complete with ETA.")

    # Take saved images and make a gif:   source --> https://pythonprogramming.altervista.org/png-to-gif/?doing_wp_cron=1693215726.9461410045623779296875
    add_to_gif(location=const["save_location"], folder="/Speed_Frames", const=const)
    add_to_gif(location=const["save_location"], folder="/Original_Frames", const=const)


# ----------- ETA DATA --------------
def load_eta(recipe, **kwargs):
    print('Loading ETA')
    with open(recipe, 'r') as filehandle:
        recipe_obj = json.load(filehandle)

    eta_engine = etabackend.eta.ETA()
    eta_engine.load_recipe(recipe_obj)

    # Set parameters in the recipe
    for arg in kwargs:
        eta_engine.recipe.set_parameter(arg, str(kwargs[arg]))

    eta_engine.load_recipe()

    return eta_engine

def get_row_from_eta(eta_engine, timetag_file, pos, context, ch_sel, run_flag):
    file_clips = eta_engine.clips(Path(timetag_file), seek_event=pos)
    result, context = eta_engine.run({"timetagger1": file_clips}, resume_task=context, return_task=True,
                                     group='qutag', max_autofeed=1)
    if result['timetagger1'].get_pos() == pos:
        # No new elements left
        run_flag = False
        #break
        return None, None, None, run_flag

    pos = result['timetagger1'].get_pos()
    row = result[ch_sel]  # [result['X']]
    return row, pos, context, run_flag


# ----------- DRAWING AND SAVING IMAGES --------------
def draw_image_heatmap(matrix, title="", fig_title="", cmap='hot', return_fig=False, save_fig=False, save_loc="misc", save_name="misc", showfig=False):
    """Generic method for any imshow() we want to do"""
    plt.figure("Q.Plot.image - " + fig_title)
    plt.imshow(matrix, cmap=cmap)
    plt.title(title)
    if save_fig:
        save_image_folder = get_image_path(save_loc)
        plt.savefig(save_image_folder.joinpath(f'{save_name}'+".png"))

def add_to_gif(location, folder, const):
    frames = []
    for i in range(1, const['nr_frames']+1):
        img = location + folder + f"/frame {i}.png"
        new_frame = Image.open(img)
        frames.append(new_frame)

    # Save into a GIF file that loops forever. gif delay time is equal to the frame time, in milliseconds
    frames[0].save(location + f"/{folder[1:-7]}_live_{const['fps']}_fps.gif", format='GIF', append_images=frames[1:], save_all=True, duration=const["frame_duration"]*1000, loop=0)   # duration given is milliseconds
    frames[0].save(location + f"/{folder[1:-7]}_set_10_fps.gif", format='GIF', append_images=frames[1:], save_all=True, duration=100, loop=0)


# ----------- DATA PROCESSING: NON-SPEED ADJUSTED --------------
def build_image_matrix(countrate_matrix, bins, dimY):
    img = []
    if bins > dimY:   # <- compressing/combining bins to get square pixels
        for row in countrate_matrix:
            combined_flipped = list(np.array(row[:int(bins / 2)]) + np.array(np.flip(row[int(bins / 2):])))
            img.append(compress_bins_into_pixels(bins=bins, pixY=dimY, row=combined_flipped))
    else:
        for row in countrate_matrix:
            combined_flipped = list(np.array(row[:int(bins / 2)]) + np.array(np.flip(row[int(bins / 2):])))
            img.append(combined_flipped)
    return img

def compress_bins_into_pixels(bins, pixY, row):
    """ Compresses bins into pixel values. argument "row" = combined row (from multiple sweeps) or a row for a single sweep"""
    compressed_list = []
    n_sweeps = 2        # here we need to account input argument "row" being one sweep, while bins includes all sweeps
    extra = int(round(bins / (n_sweeps * pixY)))   # if (bins = 40000)  --> (after we've combined two sweeps -> bins_combined = bins/2 = 20000) and  (dimY = 100)  --> bins_combined/dimY = 200  --> we need to compress every 200 values into one
    for i in range(pixY):
        pixel_sum = sum(row[i * extra:(i + 1) * extra])   # sum values in bins to make up one equally sized pixel
        compressed_list.append(pixel_sum)

    return compressed_list

# ----------- DATA PROCESSING: SPEED ADJUSTED --------------
def speed_adjusted_matrix_timebased(countrate_matrix, t_from_even_y, const):
    new_matrix = []
    count_idx = 0
    total_time = 0
    sweep_repeats = 2  # how many times we sweep the same step value, --> obs: this depends on the scan code. bidirectional raster -> 2 repeats
    countrate = np.array(countrate_matrix).flatten()
    # FIXME: instead of flattening matrix, use countrate_matrix to take data from
    try:
        for step in range(const["dimX"]):  # for each step
            sweep_rows = np.zeros((const["dimY"], sweep_repeats))   # zeros((rows, cols))  This contains the values for each row in final image
            for sweep in range(sweep_repeats):              # one for each sweep at the same step value
                accum_sweep_time = 0                        # time since start of sweep (ps)
                for y_pix in range(const["dimY"]):                   # for each pixel in sweep
                    max_pix_time = t_from_even_y[y_pix]     # gets time at that pixel since start of sweep (ps), i.e. the time we should leave the pixel, since start of sweep/half period (ps)

                    # ALTERNATIVES TO BELOW:
                    # 1) while accum_sweep_time < max_pix_time:
                    # 2) while (max_pix_time - accum_sweep_time) >= binsize/2:
                    while (max_pix_time - accum_sweep_time) >= const["binsize"]:         # continue to iterate through countrate list
                        sweep_rows[y_pix, sweep] += countrate[count_idx]        # add counts to current pixel... previously split up in two lists: "first_sweep_row", "second_sweep_row"
                        accum_sweep_time += const["binsize"]                             # add time to counter, each value in countrate occurs at "binsize" ps intervals
                        total_time += const["binsize"]                                   # total time since start to scan
                        count_idx += 1

            combined_row = np.array(sweep_rows[:, 0]) + np.flip(sweep_rows[:, 1])
            new_matrix.append(combined_row)

        return new_matrix
    except:
        print("\nERROR:")
        print(f"Progress: {len(new_matrix)} matrix rows and ({count_idx}/{len(countrate)}) values into image matrix")
        print(f"Total time spent: {total_time * 10e-12} seconds, out of {const['dimX'] * const['period_ps'] * 10e-12} seconds for full frame")
        raise

def get_t_of_y(res, ampY, frequency):
    """ returns time at each pixel edge for one sweep (first half period) """
    # res == resolution
    # ----------------
    y_even_spaced = np.linspace(start=-ampY, stop=ampY, num=res, endpoint=True)
    t_from_even = []
    for y_i in y_even_spaced:
        # get time that corresponds to sine value y_i:
        t_i = (np.arcsin(y_i / ampY) + (np.pi / 2)) / (2 * np.pi * frequency)
        t_from_even.append(t_i)
    return t_from_even, y_even_spaced

"""
def y_velocity(ampY, yfreq, time):
    # NOTE: previously called "yVelocity()"
    # Returns the velocity-fucntion for the Y function (unit volt/time) given
    # y value = ampY * np.sin(2 * np.pi * yfreq * time - (np.pi / 2))
    # y velocity = time derivative of y value
    return ampY * 2 * np.pi * yfreq * np.cos(2 * np.pi * yfreq * time - (np.pi / 2))

def get_velocity_bin_lists(y_amp, y_freq, base_bins, base_binsize):
    '''Simplified version (shortened down) of Micke's previous version, called "scan_path", to get velocity bin list'''
    realtime_list = np.arange(base_bins) * base_binsize      # Create list with "real" time (unit: ps)  --> time = step * bin-size
    y_velocity_list = [Function.y_velocity(y_amp, y_freq, t_curr) for t_curr in realtime_list]
    y_velocity_bin_list = np.array(y_velocity_list) * base_binsize  # rescale list with binsize  # create a list of y-value contributions for each time-step. Calculated as y-value = velocity * base_binsize
    #y_velocity_bin_list = np.array([Function.y_velocity(y_amp, y_freq, t_curr) * base_binsize for t_curr in realtime_list])  # rescale list with binsize  # create a list of y-value contributions for each time-step. Calculated as y-value = velocity * base_binsize
    return y_velocity_bin_list  # realtime_list, y_value_list, y_velocity_list, y_velocity_bin_list
"""
