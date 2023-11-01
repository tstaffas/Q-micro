# Packages for 3D animation/gif
from __future__ import division
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
import mpl_toolkits.mplot3d.axes3d as p3
import matplotlib.animation as animation

# Packages for 2D gif
from PIL import Image, ImageDraw

# Packages for plotting
from matplotlib import pyplot as plt

# Packages for analysis and computation
import os
from pathlib import Path
import numpy as np

# Packages for ETA backend
import json
import etabackend.eta   # Available at: https://github.com/timetag/ETA, https://eta.readthedocs.io/en/latest/
import time


"""
FLIPPING AXIS:
np.flip(matrix, axis={...})

axis=None --> flips diagonally (transpose?)
axis=0 --> flips around x axis (up-down)
axis=1 --> flips around y axis (left-right)
"""


# Fun fact: line we scan is approx 150 micrometers wide
#..... UPDATED: 3 September 2023 .....#

# ----------- FILE HANDLING --------------
def get_timres_name(folder, num, freq, clue):
    """ searches for timeres filename (that fits params) in a folder and returns the name """
    for filename in os.listdir(folder):  # checks all files in given directory (where data should be)
        if clue in filename:
            # NOTE: "clue" helps us differentiate between two with the same frequency (e.g. clue="figure_8")
            if f"numFrames({num})" in filename:
                if f"sineFreq({freq})" in filename:
                    if ".timeres" in filename:
                        #print("Using datafile:", filename)
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

    # calculate sine times needed for speed adjustment (same values for all rows, so we only need to do it once)
    t_from_even_y, y_even_spaced = get_t_of_y(res=const["dimY"], ampY=const["ampY"], frequency=const["freq_ps"])

    # --- LOAD RECIPE ---
    eta_engine = load_eta(const["eta_recipe"], bins=const["bins"], binsize=const["binsize"])  # NOTE: removed for test

    # ------ETA PROCESSING-----
    pos = 0           # internal ETA tracker (-> maybe tracks position in data list?)
    context = None    # tracks info about ETA logic, so we can extract and process data with breaks (i.e. in parts)
    image_nr = 0      # tracks which frame is being processed
    all_matrix = []   # for 3D animation

    # step 1) repeat extraction and creations of frames while there are more frames to be created
    while image_nr < const["nr_frames"]:
        countrate_frame = []   # to save data the same way it comes in (alternative to countrate list with more flexibility)
        row_nr = 0
        image_nr += 1           # note: image number starts at 1 and not 0 (i.e. not regular indexing)

        # step 2) For each frame: Extracting rows until image is filled
        while row_nr < const['dimX']:
            row_nr += 1
            row, pos, context = get_row_from_eta(eta_engine=eta_engine, pos=pos, context=context, ch_sel=const["ch_sel"], timetag_file=const["timetag_file"])
            if pos is None:
                print("CAUTION: premature break, no remaining data to extract")
                break
            countrate_frame.append(list(row))

        # At this point we have filled one full image/frame
        print(f"Frame {image_nr}/{const['nr_frames']} complete!")

        #  step 3) Flip every odd frame since we scan in different directions
        if image_nr % 2 == 1:  # note: indexing starts att 1 so odd frames are at even values of 'image_nr'
            countrate_frame = np.flip(np.array(countrate_frame))  # , axis=0)

        #  -------  PROCESS DATA INTO IMAGE: --------
        # step 4) create non-speed-adjusted image, compressing bins if needed
        #non_speed_matrix = build_image_matrix(countrate_matrix, const["bins"], const["dimY"])  # raw images, flipping comparison
        #draw_image_heatmap_3D(matrix=np.array(non_speed_matrix),  title=f"Speed adjusted - {image_nr}/{const['nr_frames']}\nScan frame rate: {const['scan_fps']} fps", fig_title=f"Speed adjusted - sine freq: {const['freq']} Hz",     save_fig=True, save_loc=const["save_location"]+"/Adjusted_Frames",    save_name=f"frame {image_nr}")

        # step 5) do speed adjustment on raw data
        adjusted_matrix = speed_adjusted_matrix_timebased(countrate_frame, t_from_even_y, const)
        all_matrix.append(np.array(adjusted_matrix))   # for 3D animation

        # step 6) create and save images of current frame:   # note: below two functions are needed to save figs and create gifs

        #   -- Draw current frame - 2D frame
        #draw_image_heatmap(matrix=np.array(non_speed_matrix), title=f"Original image - {image_nr}/{const['nr_frames']}\nScan frame rate: {const['scan_fps']} fps", fig_title=f"Non-speed adjusted - sine freq: {const['freq']} Hz", save_fig=True, save_loc=const["save_location"]+"/Original_Frames", save_name=f"frame {image_nr}")
        draw_image_heatmap(matrix=np.array(adjusted_matrix),  title=f"Speed adjusted - {image_nr}/{const['nr_frames']}\nScan frame rate: {const['scan_fps']} fps", fig_title=f"Speed adjusted - sine freq: {const['freq']} Hz",     save_fig=True, save_loc=const["save_location"]+"/Adjusted_Frames",    save_name=f"frame {image_nr}")
        #   -- Draw current frame - 3D plot:
        #draw_image_heatmap_3D(matrix=np.array(adjusted_matrix),  title=f"Speed adjusted - {image_nr}/{const['nr_frames']}\nScan frame rate: {const['scan_fps']} fps", fig_title=f"Speed adjusted - sine freq: {const['freq']} Hz",     save_fig=True, save_loc=const["save_location"]+"/Adjusted_Frames",    save_name=f"frame {image_nr}")

    print("Complete with ETA.")

    # step 7) create and save gifs with saved frames
    for i in range(len(const['gif_rates'])):
        #add_to_gif(location=const["save_location"], folder="/Original_Frames", const=const, gif_frame_rate=const['gif_rates'][i], note=const['gif_notes'][i], overlay=True)
        add_to_gif(location=const["save_location"], folder="/Adjusted_Frames", const=const, gif_frame_rate=const['gif_rates'][i], note=const['gif_notes'][i], overlay=True)

    # 3D animation
    #animate_image_heatmap_3D(all_matrix, title="3D animation", fig_title="3D animation", cmap='hot')
    plt.show()

# ----------- ETA DATA --------------
def load_eta(recipe, **kwargs):
    print('Loading ETA')
    with open(recipe, 'r') as filehandle:
        recipe_obj = json.load(filehandle)
    #print("old:\n", recipe_obj)  # remove later

    eta_engine = etabackend.eta.ETA()
    eta_engine.load_recipe(recipe_obj)

    # Set parameters in the recipe
    for arg in kwargs:
        eta_engine.recipe.set_parameter(arg, str(kwargs[arg]))

    eta_engine.load_recipe()

    print("recipe loaded")
    return eta_engine

"""
    # Create an instance of the TimeTagger
    tagger = createTimeTagger()

    # Adjust trigger level on channel 1 to -0.25 Volt
    tagger.setTriggerLevel(-1, -0.25)   # <---- negative channel for negative voltage

    # Add time delay of 123 picoseconds on the channel 3
    tagger.setInputDelay(3, 123)


    # Run Correlation for 1 second to accumulate the data
    corr.startFor(int(1e12), clear=True)
    corr.waitUntilFinished()

    # Read the correlation data
    data = corr.getData()
    """

def get_row_from_eta(eta_engine, pos, context, ch_sel, timetag_file):

    # TODO: (for new timetagger) change clips below to contain channel nr (???)
    # NOTE FORMAT TYPES:
    """
    Value   |   ETA Constant/Name        |      Format for Device
    -----------------------------------------------------------------
    0           eta.FORMAT_PQ                   PicoQuant
    1           eta.FORMAT_SI_16bytes           Swabian Instrument binary
    2           eta.FORMAT_QT_COMPRESSED        compressed qutools quTAG binary
    3           eta.FORMAT_QT_RAW               raw qutools quTAG (?)
    4           eta.FORMAT_QT_BINARY            qutools quTAG 10-byte Binary
    5           eta.FORMAT_BH_spc_4bytes        Becker & Hickl SPC-134/144/154/830
    6           eta.FORMAT_ET_A033              Eventech ET A033
    """
    eta_format = eta_engine.FORMAT_SI_16bytes

    file_clips = eta_engine.clips(Path(timetag_file), seek_event=pos, format=eta_format)   # Note this is where we provide timetag file
    # -----
    result, context = eta_engine.run({"timetagger1": file_clips}, resume_task=context, return_task=True, group='qutag', max_autofeed=1)

    if result['timetagger1'].get_pos() == pos:
        # No new elements left
        return None, None, None

    pos = result['timetagger1'].get_pos()
    row = result[ch_sel]  # [result['X']]
    return row, pos, context


# ----------- DRAWING AND SAVING IMAGES --------------
def draw_image_heatmap(matrix, title="", fig_title="", cmap='hot', save_fig=False, save_loc="misc", save_name="misc"):
    """Generic method for any imshow() we want to do"""
    matrix = np.flip(matrix, axis=1)   # flips the image because imshow() fills in from bottom (??)
    plt.figure(fig_title)
    plt.imshow(matrix, cmap=cmap)
    plt.title(title)
    plt.axis('off')
    if save_fig:
        save_image_folder = get_image_path(save_loc)
        plt.savefig(save_image_folder.joinpath(f'{save_name}'+".png"))

def draw_image_heatmap_3D(matrix, title="", fig_title="", cmap='hot'):  # , save_fig=False, save_loc="misc", save_name="misc"):
    matrix = np.flip(matrix)   # flips the image because imshow() fills in from bottom (??)

    X = np.arange(0, len(matrix[0]))
    Y = np.arange(0, len(matrix))
    X, Y = np.meshgrid(X, Y)

    plt.figure("3D "+fig_title)
    ax = plt.axes(projection='3d')
    surf = ax.plot_surface(X, Y, matrix, cmap=cmap, linewidth=0, antialiased=False)
    plt.title("3D "+title)
    plt.axis('off')
    #if save_fig:
    #    save_image_folder = get_image_path(save_loc)
    #    plt.savefig(save_image_folder.joinpath(f'3D_{save_name}'+".png"))

def animate_image_heatmap_3D(all_matrix, title="", fig_title="", cmap='hot', z_axis_lim=300):

    def data_gen(framenumber, data, plot):
        if framenumber == 0:
            time.sleep(2)
        # change matrix to next frame
        idx = framenumber % 10
        #print(idx, "/", len(all_matrix))
        data = all_matrix[idx]
        data = np.flip(data)  # flips the image because imshow() fills in from bottom (or differently than we scan??)

        # update plot with new data
        ax.clear()
        plot = ax.plot_surface(X, Y, data, **plot_args)
        plt.title(title + f" (frame: {idx+1})")
        #plt.xlim((0, 100))
        #plt.ylim((0, 100))
        ax.set_zlim(0, z_axis_lim)

        azim = 225 + 10*framenumber   # 360/10
        ax.view_init(azim=azim, elev=60.)  # ax.view_init(elev=200., azim=45)
        plt.axis('off')

        return plot,

    matrix = np.flip(all_matrix[0])  # flips the image because imshow() fills in from bottom (??)

    #plot_args = {'rstride': 1, 'cstride': 1, 'cmap': cm.bwr, 'linewidth': 0.01, 'antialiased': True, 'color': 'w', 'shade': True}  # TODO ??
    plot_args = {'rstride': 1, 'cstride': 1, 'cmap': cmap, 'linewidth': 0, 'antialiased': False, 'color': 'w', 'shade': True}  # TODO ??

    fig = plt.figure(fig_title)     # NOTE: Unsure if this goes here
    ax = plt.axes(projection='3d')  # NOTE unsure if this goes here

    # first frame
    X = np.arange(0, len(matrix[0]))
    Y = np.arange(0, len(matrix))
    # Z = np.zeros((len(matrix[0]), len(matrix))) # TODO?
    # Z[len(matrix[0])//2, len(matrix)//2] = 1  # TODO?? midpoint?
    X, Y = np.meshgrid(X, Y)

    surf = ax.plot_surface(X, Y, matrix, **plot_args)  # surf = ax.plot_surface(X, Y, matrix, cmap=cmap, linewidth=0, antialiased=False)
    plt.title(title)
    plt.xlim((0, 100))
    plt.ylim((0, 100))
    ax.set_zlim(0, z_axis_lim)  # TODO
    ax.view_init(azim=225, elev=30.)   # ax.view_init(elev=200., azim=45)
    plt.axis('off')

    anim = animation.FuncAnimation(fig, data_gen, fargs=(matrix, surf), interval=50, blit=False)

    # Alternatively save animation to gif
    #anim = animation.FuncAnimation(fig, data_gen, fargs=(matrix, surf), interval=50, repeat=True, save_count=36)
    #print("Done with animation")
    #writergif = animation.PillowWriter(fps=3)
    #anim.save("3D_animation.gif", writer=writergif)
    plt.show()

def add_to_gif(location, folder, const, gif_frame_rate, note="", overlay=False):
    # Take saved images and make a gif:
    #   altered from -> https://pythonprogramming.altervista.org/png-to-gif/?doing_wp_cron=1693215726.9461410045623779296875
    frames = []
    grey = (105, 105, 105)   # RGB color for extra text   #black = (0, 0, 0)

    for i in range(1, const['nr_frames']+1):
        img = location + folder + f"/frame {i}.png"
        new_frame = Image.open(img)

        # Additional text added to gif such as playback frame rate and timestamp of used timeres
        if overlay:
            draw_frame = ImageDraw.Draw(new_frame)
            text = f"Playback: {gif_frame_rate} fps  {note}\nScan timestamp: {const['timetag_file'][-27:-25]}/{const['timetag_file'][-29:-27]}/20{const['timetag_file'][-31:-29]} ({const['timetag_file'][-18:-9]})"
            draw_frame.text((10, 450), text, fill=grey)  # , font=font)   # TODO: maybe increase font size
        frames.append(new_frame)

    # Save into a GIF file that loops forever. gif delay time is equal to the frame time, in milliseconds
    frames[0].save(location + f"/{folder[1:-7]}_scan({const['scan_fps']}fps)_playback({gif_frame_rate}fps).gif", format='GIF', append_images=frames[1:], save_all=True, duration=1000/gif_frame_rate, loop=0)  # param: duration=1000[ms]/n[fps].  10 fps => 100 duration


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
