import os
from pathlib import Path
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.colors import LogNorm
from scipy.signal import convolve2d
import lmfit.models as fitModels  #Packages used for curve fitting  # ex. GaussianModel, ConstantModel, SkewedGaussianModel

# Packages for ETA backend
import json
import etabackend.eta  # Available at: https://github.com/timetag/ETA, https://eta.readthedocs.io/en/latest/


# PyCharm: guide to autogenerate reference docs   https://www.jetbrains.com/help/pycharm/generating-reference-documentation.html

class File:

    @staticmethod
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

    @staticmethod
    def get_timres_name(folder, freq, clue):
        """ searches for timeres filename (that fits params) in a folder and returns the name """
        for filename in os.listdir(folder):  # checks all files in given directory (where data should be)
            if clue in filename:
                # NOTE: "clue" helps us differentiate between two with the same frequency (e.g. clue="figure_8")
                if f"sineFreq({freq})" in filename:
                    if ".timeres" in filename:
                        print("Using datafile:", filename)
                        return folder + filename    # this is our found timetag_file!
        print("No matching timeres file found! :(")
        exit()

    @staticmethod
    def write_to_file(matrix_data, file_name, file_path=None, folder_name="Analysed_Data"):
        # TODO: CHECK IF THIS WORKS AS INTENDED
        # FIXME: maybe use "np.savetxt()" instead

        directory = Path(__file__).parent    # or "file_path.parent"  # Note: "Path(__file__)" is the path for this script/code file

        save_folder_path = directory.joinpath(f'{folder_name}')
        save_file_path = directory.joinpath(f'{folder_name}', f'{file_name}.txt')      #save_folder_path.joinpath(file_name+'.txt')

        # Checks if a folder exists in a directory, otherwise it creates it
        if not os.path.exists(save_folder_path):    # If folder does not exist, create it
            os.makedirs(save_folder_path)

        with open(save_file_path, 'w') as f:
            for row in matrix_data:
                string_list = [str(val) for val in row]
                string_row = ' '.join(string_list)
                f.write(string_row+"\n")
                #print("hi")

    @staticmethod
    def read_from_file(file_name, file_path=None, folder_name="Analysed_Data"):
        """ returns saved matrix data """
        # TODO: CHECK IF THIS WORKS AS INTENDED
        # FIXME: maybe use "np.loadtxt()" instead

        read_data = []
        with open(file_name, 'r') as f:
            for str_row in f:
                str_list = str_row.split(' ')       # separate string row into a list of strings (each string is a data point in row)
                # TODO: check if we need to remove a '\n' at the end of each row
                int_list = [eval(x) for x in str_list]      # convert the strings of of data to integers
                # TODO: check if we need to do int() operator on each val as well
                read_data.append(int_list)
        return read_data

    @staticmethod
    def get_image_path(folder_name):
        # Checks if image folders exists in a directory, otherwise it creates it
        directory = Path(__file__).parent  # or "file_path.parent"  # Note: "Path(__file__)" is the path for this script/code file
        save_image_path = directory.joinpath(f'{folder_name}')
        if not os.path.exists(save_image_path):  # If folder does not exist, create it
            os.makedirs(save_image_path)
        return save_image_path

class Data:
    @staticmethod
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

    @staticmethod
    def eta_segmented_analysis_noise(timetag_file, ch_sel, eta_engine, bins, dimY, flip):

        if bins > dimY:
            compress = True  # NOTE: this is if bins >> dimX, and we want a quadratic even pixel size
        else:
            compress = False  # TODO: need to test if "else -> compress" works!

        # ------ETA PROCESSING-----
        pos = 0
        context = None
        run_flag = True
        image_combined_no_flip = []
        image_combined_with_flip = []

        while run_flag:
            row, pos, context, run_flag = Data.get_row_from_eta(eta_engine, timetag_file, pos, context, ch_sel, run_flag)
            if pos is None:
                print("Noise, No new elements left to extract from ETA\n")
                break

            combined_no_flip = list(np.array(row[:int(bins / 2)]) + np.array(row[int(bins / 2):]))
            combined_flipped = list(np.array(row[:int(bins / 2)]) + np.array(np.flip(row[int(bins / 2):])))

            if compress:
                image_combined_no_flip.append(Process.compress_bins_into_pixels(bins, pixY=dimY, row=combined_no_flip))
                image_combined_with_flip.append(Process.compress_bins_into_pixels(bins, pixY=dimY, row=combined_flipped))
            else:
                image_combined_no_flip.append(combined_no_flip)
                image_combined_with_flip.append(combined_flipped)

        return image_combined_no_flip, image_combined_with_flip

    @staticmethod
    def eta_segmented_analysis_countrate(timetag_file, ch_sel, eta_engine, bins, dimY, flip, noise=0):
        print("Starting Analysis")

        # ------ETA PROCESSING-----
        pos = 0
        context = None
        run_flag = True
        list_countrate = []
        filtered_countrate = []

        while run_flag:
            row, pos, context, run_flag = Data.get_row_from_eta(eta_engine, timetag_file, pos, context, ch_sel, run_flag)
            if pos is None:
                print("Countrate, No new elements left to extract from ETA\n")
                break
            # ----
            # add to full countrate list
            list_countrate += list(row)

            filtered_countrate += list(Process.filter_countrate_row(bins, pixY=dimY, row=row[:int(bins / 2)], noise=noise))
            filtered_countrate += list(Process.filter_countrate_row(bins, pixY=dimY, row=row[int(bins / 2):], noise=noise))

        print("All elements processed.\nAnalysis Finished")
        return list_countrate, filtered_countrate

    @staticmethod
    def eta_segmented_analysis_extra(timetag_file, ch_sel, eta_engine, bins, dimY, flip):
        print("Starting Analysis")

        if bins > dimY:
            compress = True  # NOTE: this is if bins >> dimX, and we want a quadratic even pixel size
        else:
            compress = False  # FIXME: need to test if "else -> compress" works!

        #n_sweeps = 2    # how many half periods we do before stepping to next x value   # TODO: IMPLEMENT THIS IDEA EVERYWHERE!!!

        # ------ETA PROCESSING-----
        pos = 0
        context = None
        run_flag = True

        countrate_combined = []  # returning this instead

        half_combined_no_flip = []
        half_combined_with_flip = []
        second_half_flipped_img = []
        first_half_img = []
        second_half_img = []

        while run_flag:

            row, pos, context, run_flag = Data.get_row_from_eta(eta_engine, timetag_file, pos, context, ch_sel, run_flag)

            if pos is None:
                print("Extra, No new elements left to extract from ETA\n")
                break

            # ----
            first_half = row[:int(bins / 2)]  # even row
            second_half = row[int(bins / 2):]  # odd row
            second_half_flipped = np.flip(second_half.copy())
            combined_no_flip = list(np.array(first_half) + np.array(second_half))
            combined_flipped = list(np.array(first_half) + np.array(second_half_flipped))

            if compress:
                first_half_img.append(Process.compress_bins_into_pixels(bins, dimY, first_half))
                second_half_img.append(Process.compress_bins_into_pixels(bins, dimY, second_half))
                second_half_flipped_img.append(Process.compress_bins_into_pixels(bins, dimY, second_half_flipped))
                half_combined_no_flip.append(Process.compress_bins_into_pixels(bins, dimY, combined_no_flip))
                half_combined_with_flip.append(Process.compress_bins_into_pixels(bins, dimY, combined_flipped))

            else:
                first_half_img.append(first_half)
                second_half_img.append(second_half)
                second_half_flipped_img.append(second_half_flipped)  # TODO: check is we need to do list() for flipped
                half_combined_no_flip.append(combined_no_flip)
                half_combined_with_flip.append(combined_flipped)

            if flip:
                countrate_combined += combined_flipped
            else:
                countrate_combined += combined_no_flip

        first_half_img_corrected = list(np.flip(first_half_img))
        second_half_img_corrected = list(np.flip(second_half_img))

        return countrate_combined, first_half_img, second_half_img, half_combined_no_flip, half_combined_with_flip, \
               first_half_img_corrected, second_half_img_corrected, second_half_flipped_img

class MultiFrame:

    @staticmethod
    def eta_segmented_analysis_multiframe(const, return_full):
        """Extracts and processes one frame at a time. Due to this we have to do all image processing within the function
            Alternative if we want to break out of the function is that return and carry in "context", and "pos" """

        # calc. times for speed adjustment (same for all rows, so we only do it once)
        t_from_even_y, y_even_spaced = Function.get_t_of_y(res=const["dimY"], ampY=const["ampY"], frequency=const["freq_ps"])

        # --- LOAD RECIPE ---
        eta_engine = File.load_eta(const["eta_recipe"], bins=const["bins"], binsize=const["binsize"])  # NOTE: removed for test


        # ------ETA PROCESSING-----
        print("Starting MultiFrame Analysis")
        pos = 0           # internal ETA tracker (-> maybe tracks position in data list?)
        context = None    # tracks info about ETA logic, so we can extract and process data with breaks (i.e. in parts)
        image_nr = 0      # tracks which frame is being processed

        # step 1) repeat extraction and creations of frames while there are more frames to be created

        # for i in range(nr_frames()):   # note: maybe alternative condition
        #while image_nr < const["nr_frames"]: # note: maybe alternative condition
        while pos is not None:  #

            run_flag = True         # useful if runflag condition is used instead of "break"
            countrate_matrix = []   # to save data the same way it comes in (alternative to countrate list with more flexibility)
            row_nr = 0
            image_nr += 1           # note: image number starts at 1 and not 0 (i.e. not regular indexing)
            print(f"\n-------\nProcessing frame {image_nr}:")

            # step 2) Extracting rows until image is filled
            while run_flag:
                row_nr += 1
                row, pos, context, run_flag = Data.get_row_from_eta(eta_engine, const["timetag_file"], pos, context, const["ch_sel"], run_flag)

                #print("hi")
                if pos is None:
                    # Note: At this point we have gone through all data available in ETA file
                    print(f"No new elements left to extract from ETA. Ended on row {str(row_nr)}.")
                    #run_flag = False
                    break   # breaks out of inner while loop

                countrate_matrix.append(list(row))

                if row_nr == const["dimX"]:
                    # Note: At this point we have filled one full image and want to move onto the next image
                    print(f"Frame {image_nr} complete!")
                    break      # breaks out of inner while loop

            if len(countrate_matrix) > 0:  # FIXME: this is a quick fix so we don't process an empty image on last iteration

                # SAVE EXTRACTED FRAME DATA TO TEXTFILE:
                File.write_to_file(matrix_data=countrate_matrix, file_name=f"countrate_matrix_frame_{image_nr}", folder_name=const["save_location"]+"/Countrate_Data")  # , file_path=None, folder_name="")
                # Note: How to retrieve countrate data from file: --> # countrate_matrix = File.read_from_file(file_name="Analysed_Data/countrate_matrix_frame_1.txt")  # , file_path=None, folder_name="")

                # PROCESS IMAGES:
                filtered_adjusted_matrix, raw_adjusted_matrix, raw_non_speed = MultiFrame.process_image_data(countrate_matrix, const, t_from_even_y, image_nr)
                # Alternative: return full --> # countrate_raw, countrate_filtered, countrate_matrix, img_no_flip, img_with_flip, raw_adjusted_matrix, filtered_adjusted_matrix, flipped_adjusted_matrix, const = MultiFrame.process_image_data(countrate_matrix, const, t_from_even_y, image_nr)

                # PLOT AND SAVE IMAGES:
                Plot.image_heatmap(np.array(filtered_adjusted_matrix), fig_title="filtered, speed", title=f"Multi, frame {image_nr} - Filtered speed adjusted", save_fig=True, save_loc=const["save_location"]+"/Images/Filtered_Speed", save_name=f"Frame {image_nr}")
                Plot.image_heatmap(np.array(raw_adjusted_matrix),      fig_title="raw, speed",      title=f"Multi, frame {image_nr} - Raw speed adjusted",      save_fig=True, save_loc=const["save_location"]+"/Images/Raw_Speed",      save_name=f"Frame {image_nr}")
                Plot.image_heatmap(np.array(raw_non_speed),            fig_title="raw, non-speed",  title=f"Multi, frame {image_nr} - Raw non-speed adjusted",  save_fig=True, save_loc=const["save_location"]+"/Images/Raw_Non-Speed",  save_name=f"Frame {image_nr}")

                #    ---- MICKES SPEED METHOD. Not working yet.. -----
                #Sbins = const["bins"]/const['dimX']  # new -- Sbins is the number of bins per half period (per swipe up or swipe down). This must be constant
                #pixelAY = (2 * abs(const["ampY"])) / const["dimY"]  # pixelA is the total y-value (current) for each pixel. This must also be constant. E.g. if half a period goes from y value -0.05 to 0.05 = 0.1, then pixelA is 0.1/100 = 0.001
                #base_bins = const['bins']
                #base_binsize = const['binsize']
                #velocity_bin_list = Function.get_velocity_bin_lists(const["ampY"], const["freq_ps"], base_bins, base_binsize)
                #i_matrix3 = Construct.AdjustedMatrix(const["dimX"], const["dimY"], Sbins, pixelAY, velocity_bin_list, countrate_matrix)  # Method 3
                #i_matrix3 = Construct.not_working_createAdjustedMatrix(const["dimX"], const["dimY"], Sbins, pixelAY, velocity_bin_list, countrate_matrix)  # Method 3
                #Plot.image_heatmap(np.array(i_matrix3), fig_title="Micke, speed", title=f"Micke, Multi, frame {image_nr} - speed adjusted")
                #    -----

                print(f"\nAll elements processed for frame {image_nr}.")
                plt.show()

        print("Complete with ETA.")

        #if return_full:     # NOTE: temporary return while we only have one image --> later we have to restructure the code
        #   return countrate_raw, countrate_filtered, countrate_matrix, img_no_flip, img_with_flip, raw_adjusted_matrix, filtered_adjusted_matrix, flipped_adjusted_matrix, const   # we return const because it's updated with noise

    @staticmethod
    def process_image_data(countrate_matrix, const, t_from_even_y, image_nr, return_full=False):
        """takes in data extracted from ETA and does all imaging"""
        #  -------  PROCESS IMAGE DATA: --------
        # calculate background noise value based on tolerance
        img_no_flip, img_with_flip = MultiFrame.flip_no_flip_images(countrate_matrix, const["bins"], const["dimY"])  # raw images, flipping comparison
        noise = Process.get_noise_value(matrix=img_no_flip, tolerance=const["noise_tolerance"])
        const["noise"] = noise  # save noise level for this frame

        # get regular countrate, and filtered countrate (based on noise)
        countrate_raw, countrate_filtered, flipped_countrate = MultiFrame.get_countrate_lists(countrate_matrix, const, noise)

        # do speed adjustment on raw and filtered data
        raw_adjusted_matrix, _ = Construct.SpeedAdjustedMatrix_timebased(countrate_raw, t_from_even_y, const, print_progress=True)
        filtered_adjusted_matrix, _ = Construct.SpeedAdjustedMatrix_timebased(countrate_filtered, t_from_even_y, const)
        flipped_adjusted_matrix, _ = Construct.SpeedAdjustedMatrix_timebased(flipped_countrate, t_from_even_y, const)

        if return_full:
            return countrate_raw, countrate_filtered, countrate_matrix, img_no_flip, img_with_flip, raw_adjusted_matrix, filtered_adjusted_matrix, flipped_adjusted_matrix, const   # we return const because it's updated with noise
        if const["use_flip"]:
            return filtered_adjusted_matrix, raw_adjusted_matrix, img_with_flip
        return filtered_adjusted_matrix, raw_adjusted_matrix, img_no_flip

    @staticmethod
    def get_countrate_lists(countrate_matrix, const, noise):
        filtered_countrate = []
        countrate_list = []
        flipped_countrate = []

        for i, data_row in enumerate(countrate_matrix):
            countrate_list += list(data_row)

            flipped_countrate += list(np.array(data_row[:int(const["bins"] / 2)]))
            flipped_countrate += list(np.array(np.flip(data_row[int(const["bins"] / 2):])))

            filtered_countrate += list(Process.filter_countrate_row(const["bins"], pixY=const["dimY"], row=data_row[:int(const["bins"] / 2)], noise=noise))  # filtering first sweep
            filtered_countrate += list(Process.filter_countrate_row(const["bins"], pixY=const["dimY"], row=data_row[int(const["bins"] / 2):], noise=noise))  # filtering second sweep

        #print(len(countrate_list), len(flipped_countrate))
        return countrate_list, filtered_countrate, flipped_countrate

    """@staticmethod
    def noise_analysis(countrate_matrix, bins, dimY, noise_tolerance):
         '''given the data matrix we can redo/simulate the ETA data extraction '''
        if bins > dimY:
            compress = True     # NOTE: this is if bins >> dimX, and we want a quadratic even pixel size
        else:
            compress = False

        image_combined_no_flip = []
        image_combined_with_flip = []

        for data_row in countrate_matrix:
            combined_no_flip = list(np.array(data_row[:int(bins / 2)]) + np.array(data_row[int(bins / 2):]))
            combined_flipped = list(np.array(data_row[:int(bins / 2)]) + np.array(np.flip(data_row[int(bins / 2):])))

            if compress:
                image_combined_no_flip.append(Process.compress_bins_into_pixels(bins, pixY=dimY, row=combined_no_flip))
                image_combined_with_flip.append(Process.compress_bins_into_pixels(bins, pixY=dimY, row=combined_flipped))
            else:
                image_combined_no_flip.append(combined_no_flip)
                image_combined_with_flip.append(combined_flipped)

        return image_combined_no_flip, image_combined_with_flip, noise"""

    @staticmethod
    def flip_no_flip_images(countrate_matrix, bins, dimY):
        img_no_flip = []
        img_with_flip = []

        if bins > dimY:
            #compress = True  # NOTE: if bins > dimX then we need to combine bins to get square pixels
            for row in countrate_matrix:
                combined_no_flip = list(np.array(row[:int(bins / 2)]) + np.array(row[int(bins / 2):]))
                combined_flipped = list(np.array(row[:int(bins / 2)]) + np.array(np.flip(row[int(bins / 2):])))
                img_no_flip.append(Process.compress_bins_into_pixels(bins=bins, pixY=dimY, row=combined_no_flip))
                img_with_flip.append(Process.compress_bins_into_pixels(bins=bins, pixY=dimY, row=combined_flipped))

        else:
            #compress = False
            for row in countrate_matrix:
                combined_no_flip = list(np.array(row[:int(bins / 2)]) + np.array(row[int(bins / 2):]))
                combined_flipped = list(np.array(row[:int(bins / 2)]) + np.array(np.flip(row[int(bins / 2):])))
                img_no_flip.append(combined_no_flip)
                img_with_flip.append(combined_flipped)

        return img_no_flip, img_with_flip


class Process:

    @staticmethod
    def get_noise_value(matrix, tolerance):
        countrate = []
        for row in matrix:
            countrate += list(row)
        max_val = max(countrate)
        noise = tolerance*max_val
        return noise

    @staticmethod
    def compress_bins_into_pixels(bins, pixY, row):
        """ Compresses bins into pixel values. argument "row" = combined row (from multiple sweeps) or a row for a single sweep"""

        compressed_list = []
        n_sweeps = 2        # here we need to account input argument "row" being one sweep, while bins includes all sweeps
        extra = int(round(bins / (n_sweeps * pixY)))   # if (bins = 40000)  --> (after we've combined two sweeps -> bins_combined = bins/2 = 20000) and  (dimY = 100)  --> bins_combined/dimY = 200  --> we need to compress every 200 values into one

        for i in range(pixY):
            pixel_sum = Process.get_pixel_sum(row, i, extra)  # sum values in bins to make up one equally sized pixel  --> returns sum(row[i*extra : (i+1)*extra])
            compressed_list.append(pixel_sum)

        return compressed_list

    @staticmethod
    def filter_countrate_row(bins, pixY, row, noise):
        filtered_row = []
        n_sweeps = 2        # here we need to account input argument "row" being one sweep, while bins includes all sweeps
        extra = int(round(bins / (n_sweeps * pixY)))   # if (bins = 40000)  --> (after we've combined two sweeps -> bins_combined = bins/2 = 20000) and  (dimY = 100)  --> bins_combined/dimY = 200  --> we need to compress every 200 values into one

        for i in range(pixY):
            pixel_sum = Process.get_pixel_sum(row, i, extra)  # sum values in bins to make up one equally sized pixel
            if pixel_sum < noise:  # noise:  TODO!! Fix if this test works
                filtered_row += list(np.zeros(extra))
            else:
                filtered_row += list(row[i * extra:(i + 1) * extra])

        return filtered_row

    @staticmethod
    def get_pixel_sum(row, i, extra):
        return sum(row[i * extra:(i + 1) * extra])  # sum values in bins to make up one equally sized pixel

    @staticmethod
    def try_noise_filter(matrix, noise_tolerance):
        noise = Process.get_noise_value(matrix, noise_tolerance)

        a_matrix = np.array(matrix)   # TODO: Test and maybe remove
        filtered_matrix = np.where(a_matrix < noise, 0, a_matrix)
        noise_mask = np.where(a_matrix <= noise, 0, 1)

        print("test, matrix size:", len(a_matrix[0]),",", len(a_matrix))

        return filtered_matrix, noise_mask

    @staticmethod
    def pass_filters(matrix_in, thresh):
        # TODO:  SEE IF WE CAN REMOVE THIS OR MERGE SOMEWHERE ELSE!!!

        use_hp_filter = use_lp_filter = True # TODO:  temp fix

        if use_hp_filter and use_lp_filter:
            ima_matrix = Process.low_filter(matrix=np.array(matrix_in), lower_thresh=thresh, lower_val=0)
            ima_matrix = Process.high_filter(matrix=np.array(ima_matrix), upper_thresh=thresh, upper_val=thresh+1)  # max() in "upperval" ensures we don't accidentally filter high values at some point

        elif use_lp_filter:
            ima_matrix = Process.low_filter(matrix=np.array(matrix_in), lower_thresh=thresh, lower_val=0)
        elif use_hp_filter:
            ima_matrix = Process.high_filter(matrix=np.array(matrix_in), upper_thresh=thresh, upper_val=thresh+1)  # max() in "upperval" ensures we don't accidentally filter high values at some point

        else:
            ima_matrix = np.array(matrix_in)
        return ima_matrix

    """@staticmethod
    def blur_before_filter(matrix, kernel, iter, thresh):
        #part from --> previously called 'final_transforms_and_plots'  
        mask_matrix = Process.binary_filter(matrix=np.array(matrix), thresh=thresh, low=0, high=1)

        blur_matrix = Process.convolver(image=np.array(matrix), kernel=kernel, iterations=iter)
        #low_matrix = Process.low_filter(matrix=np.array(blur_matrix), lower_thresh=thresh, lower_val=0)  # pass_matrix = pass_filters(blur_matrix, thresh=thresh)
        #mask_matrix = Process.high_filter(matrix=np.array(low_matrix), upper_thresh=thresh, upper_val=1)  # pass_matrix = pass_filters(blur_matrix, thresh=thresh)

        ima_matrix = low_matrix
        maskon_matrix = mask_matrix*blur_matrix


        return blur_matrix, low_matrix, mask_matrix, ima_matrix, maskon_matrix
"""

    """@staticmethod
    def filter_before_blur(matrix, kernel, iter, thresh):
        # part from --> previously called 'final_transforms_and_plots'

        low_matrix = Process.low_filter(matrix=np.array(matrix), lower_thresh=thresh, lower_val=0)  # pass_matrix = pass_filters(matrix, thresh=thresh)
        blur_matrix = Process.convolver(image=low_matrix, kernel=kernel, iterations=iter)
        mask_matrix = Process.high_filter(matrix=np.array(blur_matrix), upper_thresh=thresh, upper_val=1)  # pass_matrix = pass_filters(blur_matrix, thresh=thresh)
        ima_matrix = blur_matrix

        return blur_matrix, low_matrix, mask_matrix, ima_matrix"""

    @staticmethod
    def high_filter(matrix, upper_thresh, upper_val):
        """replace values with "upper_val" that fulfill condition "filtered_matrix >= threshold"""
        high_matrix = np.where(matrix > upper_thresh, upper_val, matrix)
        return high_matrix

    @staticmethod
    def low_filter(matrix, lower_thresh, lower_val=0):
        """replace values with "lower_val" that fulfill condition "filtered_matrix < threshold"""
        low_matrix = np.where(matrix <= lower_thresh, lower_val, matrix)
        return low_matrix

    @staticmethod
    def binary_filter(matrix, thresh, low=0, high=1):
        """binary mask with high and low values"""
        mask_matrix = np.where(matrix > thresh, high, low)  # np.where({condition to test truth}, {value if True}, {value if False})
        return mask_matrix

    @staticmethod   # TODO: CLEAN UP MESS
    def edge_detection(i_matrix, new_option):
        """  """
        ker = {
            'laplace': np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]]),   # good for edge detection, center 8
            'up_edge': np.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]]),
            'down_edge': np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]]),
            'right_edge': np.array([[1, 0, -1], [2, 0, -2], [1, 0, -1]]),
            'left_edge': np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]),
        }

        if new_option:
            edge_matrix = np.abs(convolve2d(in1=i_matrix, in2=ker['laplace'], mode='full', boundary='fill'))
            #edge_matrix_2 = np.abs(convolve2d(in1=i_matrix, in2=ker['laplace'], mode='full', boundary='wrap'))
            #edge_matrix_3 = np.abs(convolve2d(in1=i_matrix, in2=ker['laplace'], mode='full', boundary='symm'))
            #edge_matrix_4 = np.abs(convolve2d(in1=i_matrix, in2=ker['laplace'], mode='full', boundary='fill'))
            #edge_matrix_5 = np.abs(convolve2d(in1=i_matrix, in2=ker['laplace'], mode='valid', boundary='fill'))
            #edge_matrix_6 = np.abs(convolve2d(in1=i_matrix, in2=ker['laplace'], mode='same', boundary='fill'))

            #fig, ((ax1, ax2, ax3), (ax4, ax5, ax6)) = plt.subplots(2, 3, num="compare boundary for convolve2d for laplace")
            #ax1.imshow(edge_matrix, cmap='hot')
            #ax2.imshow(edge_matrix_2, cmap='hot')
            #ax3.imshow(edge_matrix_3, cmap='hot')
            #ax4.imshow(edge_matrix_4, cmap='hot')
            #ax5.imshow(edge_matrix_5, cmap='hot')
            #ax6.imshow(edge_matrix_6, cmap='hot')
            #ax1.set_title("full - FILL")
            #ax2.set_title("full - WRAP")
            #ax3.set_title("full - SYMM")
            #ax4.set_title("FULL - fill")
            #ax5.set_title("VALID - fill")
            #ax6.set_title("SAME - fill")

        else:
            edge_1 = convolve2d(i_matrix, ker['up_edge'], 'valid')
            edge_2 = convolve2d(i_matrix, ker['down_edge'], 'valid')
            edge_3 = convolve2d(i_matrix, ker['left_edge'], 'valid')
            edge_4 = convolve2d(i_matrix, ker['right_edge'], 'valid')
            edge_matrix = np.abs(edge_1) + np.abs(edge_2) + np.abs(edge_3) + np.abs(edge_4)

        return edge_matrix

    @staticmethod
    def convolver(image, kernel, iterations):
        # TODO: go through to understand and maybe improve/change

        # TODO: double-check these kernels and test them out
        # NOTE: first one is not an identity matrix, check if correct
        kernel_dict = {'identity': np.array([[0, 0, 0], [0, 1, 0], [0, 0, 0]]),
                       'blur': (1 / 90.0) * np.array([[1, 1, 1], [1, 1, 1], [1, 1, 1]]),
                       'gauss33': (1 / 16.0) * np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]]),
                       'gauss55': (1 / 256.0) * np.array([[1, 4, 6, 4, 1], [4, 16, 24, 16, 4], [6, 24, 36, 24, 6], [4, 16, 24, 16, 4], [1, 4, 6, 4, 1]]),
                       'sharpen': np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]),
                       }
        conv_filter = kernel_dict[kernel]
        for i in range(iterations):
            image = convolve2d(image, conv_filter, 'same', boundary='fill', fillvalue=0)
        return image

    @staticmethod
    def smoothing_iteratively(countrate, iterations):
        for j in range(iterations):
            smooth_countrate = [countrate[0]]
            for i in range(1, len(countrate)-1):
                avg_val = (countrate[i-1] + countrate[i+1])/2
                smooth_countrate.append(avg_val)
            smooth_countrate.append(countrate[-1])

            countrate = smooth_countrate

        return smooth_countrate

    @staticmethod
    def smoothing_directly(countrate, iterations):
        for j in range(iterations):
            for i in range(1, len(countrate)-1):
                countrate[i] = (countrate[i-1] + countrate[i+1])/2

        return countrate


class Function:
    """ Functions to adjust image for variable swipe-speeds """

    @staticmethod
    def y_value(ampY, yfreq, time):
        # NOTE: previously called "yValue()"
        # Returns the function for the Y value for the swipe function (unit volt)
        return ampY * np.sin(2 * np.pi * yfreq * time - (np.pi / 2))  # Phase pi/2 to start on peak or valley

    @staticmethod
    def y_velocity(ampY, yfreq, time):
        # NOTE: previously called "yVelocity()"
        # Returns the velocity-fucntion for the Y function (unit volt/time) given
        return ampY * 2 * np.pi * yfreq * np.cos(2 * np.pi * yfreq * time - (np.pi / 2))

    @staticmethod
    def time_from_sine(y_i, ampY, frequency):
        """ Returns the corresponing time value given a y value """
        # y = ampY * np.sin(2 * np.pi * f * t - (np.pi / 2))
        # y/ampY = np.sin(2 * np.pi * f * t - (np.pi / 2))
        # np.arcsin(y/ampY) =  (2 * np.pi * f * t) - (np.pi / 2)
        # np.arcsin(y/ampY) + (np.pi / 2) =  (2 * np.pi * f * t)
        # ( np.arcsin(y/ampY) + (np.pi / 2) ) / (2 * np.pi * f ) =  t
        # -->
        t_i = (np.arcsin(y_i / ampY) + (np.pi / 2)) / (2 * np.pi * frequency)
        return t_i

    @staticmethod
    def get_t_of_y(res, ampY, frequency):
        """ returns time at each pixel edge for one sweep (first half period) """
        # res == resolution
        # ----------------
        y_even_spaced = np.linspace(start=-ampY, stop=ampY, num=res, endpoint=True)
        t_from_even = []
        for y_i in y_even_spaced:
            t_i = Function.time_from_sine(y_i, ampY, frequency)
            t_from_even.append(t_i)
        return t_from_even, y_even_spaced

    @staticmethod
    def get_y_of_t(res, ampY, frequency):
        half_period = 1/(2*frequency)
        t_even_spaced = np.linspace(start=0, stop=half_period, num=res, endpoint=True)
        y_from_even = []
        for t_j in t_even_spaced:
            y_j = Function.y_value(ampY, frequency, t_j)
            y_from_even.append(y_j)
        # ----------------
        return t_even_spaced, y_from_even

    @staticmethod
    def get_velocity_bin_lists(y_amp, y_freq, base_bins, base_binsize):
        """ Simplified version (shortened down) of Micke's previous version, called "scan_path", to get velocity bin list"""
        realtime_list = np.arange(base_bins) * base_binsize      # Create list with "real" time (unit: ps)  --> time = step * bin-size
        #y_value_list = [Function.y_value(y_amp, y_freq, t_curr) for t_curr in realtime_list]
        y_velocity_list = [Function.y_velocity(y_amp, y_freq, t_curr) for t_curr in realtime_list]
        y_velocity_bin_list = np.array(y_velocity_list) * base_binsize  # rescale list with binsize  # create a list of y-value contributions for each time-step. Calculated as y-value = velocity * base_binsize

        #y_velocity_bin_list = np.array([Function.y_velocity(y_amp, y_freq, t_curr) * base_binsize for t_curr in realtime_list])  # rescale list with binsize  # create a list of y-value contributions for each time-step. Calculated as y-value = velocity * base_binsize

        return y_velocity_bin_list  # realtime_list, y_value_list, y_velocity_list, y_velocity_bin_list


class Construct:
    """ Image construction """

    # TODO: create a new Speed adjusted matrix trying a different method than accumulating time

    @staticmethod
    def SpeedAdjustedMatrix_timebased(countrate, t_from_even_y, const, print_progress=False):
        #dimX, dimY, binsize, period, flip
        #const["dimX"], const["dimY"], const["binsize"], const["period_ps"], flip = const["use_flip"]
        remaining_pixel_times = []
        new_matrix = []
        count_idx = 0
        total_time = 0
        sweep_repeats = 2  # how many times we sweep the same step value, --> obs: this depends on the scan code. bidirectional raster -> 2 repeats
        # print(f"\nOne binsize = {round(binsize*10e-12, 12)}")

        try:
            for step in range(const["dimX"]):  # for each step
                sweep_rows = np.zeros((const["dimY"], sweep_repeats))   # zeros((rows, cols))  This contains the values for each row in final image

                for sweep in range(sweep_repeats):              # one for each sweep at the same step value
                    accum_sweep_time = 0                        # time since start of sweep (ps)
                    for y_pix in range(const["dimY"]):                   # for each pixel in sweep
                        max_pix_time = t_from_even_y[y_pix]     # gets time at that pixel since start of sweep (ps), i.e. the time we should leave the pixel, since start of sweep/half period (ps)

                        # ALTERNATIVES TO BELOW: 1) while accum_sweep_time < max_pix_time:  2) while (max_pix_time - accum_sweep_time) >= binsize/2:
                        while (max_pix_time - accum_sweep_time) >= const["binsize"]:         # continue to iterate through countrate list
                            sweep_rows[y_pix, sweep] += countrate[count_idx]        # add counts to current pixel... previously split up in two lists: "first_sweep_row", "second_sweep_row"
                            accum_sweep_time += const["binsize"]                             # add time to counter, each value in countrate occurs at "binsize" ps intervals
                            total_time += const["binsize"]                                   # total time since start to scan
                            count_idx += 1

                        remaining_pixel_times.append(max_pix_time - accum_sweep_time)  # this is to plot how much is left to fill pixel when we meet condition to move on
                        # TODO: plot ^ and draw a horizontal line for binsize/2 or binsize to double-check the "while" condition
                    #print(f"total sweep time (sweep {sweep+1}): {round(accum_sweep_time*10e-12, 12)}/{0.5*period*10e-12} seconds")
                #print("")
                # TODO: check that it works to flip too!  and CHECK TO MAKE SURE WE ADD ELEMENT WISE
                if const["use_flip"]:
                    combined_row = np.array(sweep_rows[:, 0]) + np.flip(sweep_rows[:, 1])
                else:
                    combined_row = np.array(sweep_rows[:, 0]) + np.array(sweep_rows[:, 1])

                new_matrix.append(combined_row)
            if print_progress:
                print("\nImage complete:")
                print(f"Progress: {len(new_matrix)} matrix rows and ({count_idx}/{len(countrate)}) values into image matrix")
                print(f"Total time spent: {total_time * 10e-12} seconds, out of {const['dimX'] * const['period_ps'] * 10e-12} seconds for full frame")
                print(f"Missing time: {const['dimX'] * const['period_ps'] - total_time} picoseconds")
            return new_matrix, remaining_pixel_times
        except:
            print("\nERROR:")
            print(f"Progress: {len(new_matrix)} matrix rows and ({count_idx}/{len(countrate)}) values into image matrix")
            print(f"Total time spent: {total_time * 10e-12} seconds, out of {const['dimX'] * const['period_ps'] * 10e-12} seconds for full frame")
            raise

    @staticmethod
    def XYMatrix(dimX, dimY, pixelAY, ampY, xvaluelist, yvaluelist, countrate):
        """
            Method 1: Create a speed adjusted pixel matrix.
                based on a generalized method for resonant scanning i y-direction and stepwise in x-direction.
                This method be generalized further independent of scanning patterns in x- and y-direction
        """
        imagematrix = [[0]*dimY for i in range(dimX)] # create a 100x100 pixel matrix for the image

        yRail = []
        for i in range(dimY): #Create a list with total current over the full intervall (2 * amp) divided into each pixel segment. This will be used to made decision which pixel bin to place the counts
            yRail.append(-ampY + i * pixelAY)

        xRail = []
        for i in range(dimX): #Same function as for yrail. This is not used when stepwise but should be modified if we use a resonant function also in the x-direction
            xRail.append(i)

        indexY = 0
        indexX = 0

        for i in range(len(yvaluelist)): #
            indexX = xvaluelist[i] #Modified xvaluelsit
            for j in range(1, len(yRail)):
                if yvaluelist[i] >= yRail[j-1] and yvaluelist[i] < yRail[j]:
                    indexY = j
            imagematrix[indexX][indexY] += countrate[i]
        return imagematrix

    @staticmethod
    def XYMatrix2(dimX, dimY, pixelAY, pixelAX, ampY, ampX, xvaluelist2, yvaluelist, countrate):
        """
            Method 2: Create a speed adjusted pixel matrix
                based on a generalized method for resonant scanning i both x- and y-direction
        """
        imagematrix = [[0]*dimY for i in range(dimX)] # create a 100x100 pixel matrix for the image

        yRail = []
        for i in range(dimY): #Create a list with total current over the full intervall (2 * amp) divided into each pixel segment. This will be used to made decision which pixel bin to place the counts
            yRail.append(-ampY + i * pixelAY)

        xRail = []
        for i in range(dimX): #Same function as for yrail. This is not used when stepwise but should be modified if we use a resonant function also in the x-direction
            xRail.append(-ampX + i * pixelAX)

        indexY = 0
        indexX = 0

        for i in range(len(yvaluelist)):
            for j in range(1, len(xRail)):
                if xvaluelist2[i] >= xRail[j-1] and xvaluelist2[i] < xRail[j]:
                    indexX = j
            for k in range(1, len(yRail)):
                if yvaluelist[i] >= yRail[k-1] and yvaluelist[i] < yRail[k]:
                    indexY = k
            imagematrix[indexX][indexY] += countrate[i]
        return imagematrix


    @staticmethod
    def createAdjustedMatrix(dimX, dimY, Sbins, pixelAY, velocitybinlist, countrate):
        countrate = np.array(countrate).flatten()
        pixelpart = [0] * dimY  # number of pixels along resonant axis for one swipe up or down (half a period)
        matrix = []
        k = 0
        pixelsum = 0
        ss = 0
        for i in range(dimX):  # for each pixel in x-direction

            for j in range(len(pixelpart)):  # over each 100 pixels in y-direction (one swipe)
                # print("x-pixel:" + str(i))
                # print("y-pixel:" + str(j))
                while pixelsum < pixelAY and ss < Sbins:  # conditions that must be met during each swipe
                    pixelsum += abs(velocitybinlist[k])  # as long as the cumulative current contribution is less or equal to pixelA (the constant current per pixel)...
                    pixelpart[j] += countrate[k]  # ...sum the photon counts to the pixel j
                    # print("bin nr: " + str(k))
                    # print("swipe bin nr: " + str(ss))
                    k += 1
                    ss += 1
                print("y pixel:", j, ", pixelsum=", pixelsum, "<", pixelAY, "=pixelAY", ", k=", k)
                pixelsum = 0  # clear

            ss = 0  # clear
            if (i + 1) % 2 != 1:
                pixelpart.reverse()  # every even line segment flips
                t = 1
            matrix.append(pixelpart)
            pixelpart = [0] * dimY  # clear
        return matrix

    @staticmethod
    def AdjustedMatrix(dimX, dimY, Sbins, pixelAY, velocity_bin_list, countrate):
        """
            Method 3. Create a speed-adjustment pixel matrix
                place the right number of bins in each pixel given the swipe speed
        """
        countrate = np.array(countrate).flatten()
        plt.figure("Micke: Velocity bin list")
        plt.plot(velocity_bin_list)
        plt.show()

        #tempList = []
        matrix = []
        k = 0  # bin number
        try:
            for step in range(dimX):  # for each pixel in x-direction
                ss = 0                      # = swipe bin nr --> reset every step
                pixel_part = [0] * dimY     # clear every step  # = number of pixels along sine axis for one sweep up or down (half a period) # QUESTION ??????
                #tempList.append(step*100)
                for sweep_pix in range(dimY):  # for each pixel in y-direction (half period)
                    pixel_sum = 0  # reset sum
                    while pixel_sum < pixelAY: # and ss < Sbins:  # conditions that must be met during each swipe
                        # FIXME: k needs to account for our new scanning structure
                        pixel_sum += abs(velocity_bin_list[k])  # as long as the cumulative voltage contribution is less or equal to pixelA (the constant voltage per pixel)...
                        #print(pixel_part[sweep_pix])
                        #print(countrate[k])
                        pixel_part[sweep_pix] += countrate[k]  # add more photon counts to the pixel "sweep_pix"
                        k += 1
                        ss += 1
                    print("y pixel:", sweep_pix, ", pixelsum=", pixel_sum, "<", pixelAY, "=pixelAY")

                """if (step+1) % 2 != 1:
                    pixel_part.reverse()  # every even line segment flips
                    t = 1"""            # NOTE: now we have bidirectional scanning
                matrix.append(pixel_part)
            return matrix
        finally:
            print("\n ERRRORR:----")
            print("k:", k)
            print("pixelsum=", pixel_sum)
            print("size matrix:", len(matrix), len(matrix[0]))
            raise

    @staticmethod
    def not_working_createAdjustedMatrix(dimX, dimY, Sbins, pixelAY, velocitybinlist, countrate):
        countrate = np.array(countrate).flatten()
        pixelpart = [0] * dimY  # number of pixels along resonant axis for one swipe up or down (half a period)
        matrix = []
        k = 0
        pixelsum = 0
        ss = 0
        tempList = []  # J

        for i in range(dimX):  # for each pixel in x-direction
            print("x =", i, ", k=", k/200, "%")
            for sweep in range(1):  # one for each sweep at the same step value
                for j in range(dimY):  # over each 100 pixels in y-direction (one swipe)
                    while pixelsum < pixelAY and ss < Sbins:  # conditions that must be met during each swipe
                        pixelsum += abs(velocitybinlist[k]*200)  # as long as the cumulative current contribution is less or equal to pixelA (the constant current per pixel)...
                        pixelpart[j] += countrate[k]  # ...sum the photon counts to the pixel j
                        # print("bin nr: " + str(k))
                        # print("swipe bin nr: " + str(ss))
                        k += 1
                        ss += 1
                    tempList.append(k)
                    #print("y pixel:", j, ", pixelsum=", pixelsum, "<", pixelAY, "=pixelAY", ", k%=", k/200, "%")
                    pixelsum = 0  # clear

                tempList.append(0)

                ss = 0  # clear
                if (i + 1) % 2 != 1:
                    #pixelpart.reverse()  # every even line segment flips
                    #t = 1
                    pass
                matrix.append(pixelpart)
                pixelpart = [0] * dimY  # clear
        plt.figure("templist")
        plt.plot(tempList)
        plt.plot(tempList, 'r*')
        plt.show()

        return matrix

    @staticmethod
    def EqualMatrix(dimX, dimY, Sbins, countrate):
        """
            Method 4. Create a non speed adjusted pixel matrix
                places an equal amount of bins in each pixel
        """
        num_pix = int(Sbins / dimY)
        pixel_part = [0] * dimY
        matrix = []
        k = 0

        for i in range(dimX):
            for j in range(len(pixel_part)):
                for l in range(num_pix):
                    pixel_part[j] += countrate[k]
                    k +=1
            if (i+1) % 2 != 1:
                pixel_part.reverse()
                t = 1
            matrix.append(pixel_part)
            pixel_part = [0] * dimY
        return matrix

    @staticmethod
    def OriginalImage(dimX, dimY, resY, Sbins, countrate): #In this method Sbins = dimY
        """
            Method 5. Notice this is the original method that only works for resY = 1e10, where Sbins = dimY = 100.
            Thus, each bin is a pixel in the y-direction (100 bins = 100 pixels in y-direction)
        """
        r = int(Sbins)
        matrix = []

        for i in range(1, dimX+1):
            part = list(countrate[(i-1)*r:i*r]) #extract a line segment of Sbins = dimY
            if i % 2 != 1:
                part.reverse() # every even line segment flips
                t = 1 # just to have something within the condition if there is no even i
            matrix.append(part)
        return matrix


class Plot:
    @staticmethod
    def plot_flip_diff(const):
        """complete/standalone method to show how flipping rows affects the image"""
        eta_engine = File.load_eta(const["eta_recipe"], bins=const["bins"], binsize=const["binsize"])

        if const["bins"] > const["dimY"]:
            compress = True  # NOTE: this is if bins >> dimX, and we want a quadratic even pixel size
        else:
            compress = False  # FIXME: need to test if "else -> compress" works!

        # ------ETA PROCESSING-----
        pos = 0
        context = None
        run_flag = True
        half_combined_no_flip = []
        half_combined_with_flip = []
        second_half_flipped_img = []
        first_half_img = []
        second_half_img = []

        while run_flag:
            row, pos, context, run_flag = Data.get_row_from_eta(eta_engine, const["timetag_file"], pos, context, const["ch_sel"], run_flag)
            if pos is None:
                break
            # ----
            first_half = row[:int(const["bins"] / 2)]  # even row
            second_half = row[int(const["bins"] / 2):]  # odd row
            second_half_flipped = np.flip(second_half.copy())
            combined_no_flip = list(np.array(first_half) + np.array(second_half))
            combined_flipped = list(np.array(first_half) + np.array(second_half_flipped))

            if compress:
                first_half_img.append(Process.compress_bins_into_pixels(const["bins"], const["dimY"], first_half))
                second_half_img.append(Process.compress_bins_into_pixels(const["bins"], const["dimY"], second_half))
                second_half_flipped_img.append(Process.compress_bins_into_pixels(const["bins"], const["dimY"], second_half_flipped))
                half_combined_no_flip.append(Process.compress_bins_into_pixels(const["bins"], const["dimY"], combined_no_flip))
                half_combined_with_flip.append(Process.compress_bins_into_pixels(const["bins"], const["dimY"], combined_flipped))
            else:
                first_half_img.append(first_half)
                second_half_img.append(second_half)
                second_half_flipped_img.append(second_half_flipped)
                half_combined_no_flip.append(combined_no_flip)
                half_combined_with_flip.append(combined_flipped)

        Plot.subplots_img_2(const["dimX"], const["dimY"], first_half_img, second_half_img, half_combined_no_flip, half_combined_with_flip, second_half_flipped_img)

    @staticmethod
    def test_imshow_order(n=5):
        """ plots imshow in increasing intensity so we can see in what order it is drawn"""
        test_img = []
        for i in range(n):
            row = []
            for j in range(n):
                row.append(n * i + j)
            test_img.append(row)
        plt.figure("Q.Plot.test_imshow")
        plt.imshow(test_img)
        plt.colorbar()
        plt.show()

    # TODO: TEST AND FIX BELOW
    @staticmethod
    def test_blur(image_combined_no_flip, noise_mask):
        """testing blur with mask on non-speed adjusted image"""
        blur_matrix = Process.convolver(image=np.array(image_combined_no_flip), kernel='gauss33', iterations=1)
        ima_matrix = blur_matrix * noise_mask
        edge_matrix = Process.edge_detection(i_matrix=ima_matrix, new_option=False)
        edge_matrix_laplace = Process.edge_detection(i_matrix=ima_matrix, new_option=True)
        Plot.edge_detect(image_combined_no_flip, blur_matrix, ima_matrix, edge_matrix, edge_matrix_laplace, np.array(noise_mask))

    @staticmethod
    def image_heatmap(matrix, title="", fig_title="", cmap='hot', return_fig=False, save_fig=False, save_loc="misc", save_name="misc"):
        """Generic method for any imshow() we want to do"""
        fig = plt.figure("Q.Plot.image - " + fig_title)
        plt.imshow(matrix, cmap=cmap)
        plt.title(title)
        if save_fig:
            save_image_folder = File.get_image_path(save_loc)
            plt.savefig(save_image_folder.joinpath(f'{save_name}'+".png"))
        if return_fig:
            return fig

    @staticmethod
    def full_countrate(full_countrate):
        plt.figure("Q.Plot.full_countrate")
        plt.plot(full_countrate)
        plt.title("Full Countrate")
        plt.xlabel("bins")
        plt.ylabel("events")

    @staticmethod
    def binary_mask(mask_image):
        plt.figure("Q.Plot.binary_mask")
        plt.imshow(np.array(mask_image), cmap='hot')

    @staticmethod
    def histo_distribution(matrix, title):
        countrate = []

        if type(matrix[0]) is np.float64:  # if matrix is actually a list
            countrate = matrix
        else:
            for row in matrix:
                countrate += list(row)

        plt.figure("Q.Plot.visualize_distribution - "+title)
        plt.hist(countrate, bins=list(range(0, max(countrate)+1)), align='right')
        plt.xlabel("Value")
        plt.ylabel("Frequency")
        plt.title("Distribution of values in countrate")

    @staticmethod
    def draw_time_for_each_pixel(res, ampY, frequency):
        t_from_even, y_even_spaced = Function.get_t_of_y(res, ampY, frequency)
        t_even_spaced, y_from_even = Function.get_y_of_t(res, ampY, frequency)
        x_min = - (t_even_spaced[-1]/100)

        plt.figure("Q.Plot.draw_time_for_each_pixel - t(y)")
        plt.plot(t_from_even, y_even_spaced)
        plt.plot(t_from_even, y_even_spaced, 'b.')
        plt.xlabel("time [ps]")
        plt.ylabel("sweep position [V]")
        plt.title("t(y) -> times based on even y")
        plt.hlines(y=0, xmin=0, xmax=t_from_even[-1], colors='black')
        for k in range(res):
            plt.hlines(y=y_even_spaced[k], xmin=x_min, xmax=t_from_even[k], linestyles='--', colors='blue')
            if y_even_spaced[k] < 0:
                plt.vlines(x=t_from_even[k], ymin=y_even_spaced[k], ymax=0, linestyles='-', colors='red')
            else:
                plt.vlines(x=t_from_even[k], ymin=0, ymax=y_even_spaced[k], linestyles='-', colors='red')
        # ----------------

        plt.figure("Q.Plot.draw_time_for_each_pixel - y(t)")
        plt.plot(t_even_spaced, y_from_even)
        plt.plot(t_even_spaced, y_from_even, 'b.')
        plt.xlabel("time [ps]")
        plt.ylabel("sweep position [V]")
        plt.title("y(t) -> y based on even times")
        plt.hlines(y=0, xmin=x_min, xmax=t_even_spaced[-1], colors='black')
        for k in range(res):
            plt.hlines(y=y_from_even[k], xmin=x_min, xmax=t_even_spaced[k], linestyles='-', colors='red')
            if y_even_spaced[k] < 0:
                plt.vlines(x=t_even_spaced[k], ymin=y_from_even[k], ymax=0, linestyles='--', colors='blue')
            else:
                plt.vlines(x=t_even_spaced[k], ymin=0, ymax=y_from_even[k], linestyles='--', colors='blue')
        # ----------------
        # plt.show()

    @staticmethod # option for subplots
    def fourier_all(images, metrics, name, subplts):
        """ Calculate and plot all fourier transform given which metric """
        if subplts:
            # images = [ima_matrix, filter_im, edge_matrix]
            # metrics = ["counts", "counts_filter", "counts_edge"]

            # ------
            fig = plt.figure(f"Q.Plot.fourier_all - {name}")  # constrained_layout=True)
            subfigs = fig.subfigures(1, len(images))   # (rows, cols)

            # NOTE: metric_idx = col_inx
            for col_idx, subfig in enumerate(subfigs.flat):
                image = images[col_idx] + 1
                metric = metrics[col_idx]
                subfig.suptitle(f'{metric}')

                f = np.fft.fft2(image)                  # TODO: look into ... "2-dimensional discrete Fourier Transform."
                f_s = np.fft.fftshift(f)                # TODO: look into ... "Shift the zero-frequency component to the center of the spectrum."
                #img_i = np.fft.irfft2(f, image.shape)   # TODO: look into ... "Computes inverse of 2D disc. Fourier Transform"

                #inner_imgs = [image, img_i, np.log(abs(f_s))]
                #inner_titles = ["Raw", "Inverse Fourier", "Fourier"]
                #inner_cmaps = ['gray', 'gray', 'gray']

                #inner_imgs = [image, np.log(abs(f_s))]
                #inner_titles = ["Gray", "Fourier"]
                #inner_cmaps = ['gray', 'gray']

                inner_imgs = [image, np.log(abs(f_s))]
                inner_titles = ["2D Fourier", "log(Shifted)"]
                inner_cmaps = ['hot', 'hot']

                axs = subfig.subplots(len(inner_imgs), 1)   # (rows, cols)

                for row_idx, ax in enumerate(axs.flat):
                    ax.set_xticks([])
                    ax.set_yticks([])
                    #ax.set_title(f'inner={row_idx}', fontsize='small')
                    ax.set_title(inner_titles[row_idx], fontsize='small')
                    ax.imshow(inner_imgs[row_idx], cmap=inner_cmaps[row_idx])

        else:
            for i in range(len(images)):
                Plot.fourier(images[i], metrics[i], name)

    @staticmethod # subplots
    def fourier(image, metric, name):
        """ Calculate and plot fourier transform given which metric """
        image += 1
        f = np.fft.fft2(image)                  # TODO: look into
        f_s = np.fft.fftshift(f)                # TODO: look into
        img_i = np.fft.irfft2(f, image.shape)   # TODO: look into

        #plt.figure(num=None, figsize=(10, 8), dpi=150)
        fig, (ax1, ax2, ax3) = plt.subplots(nrows=1, ncols=3, figsize=(13, 5), num=f"Q.Plot.fourier - {metric}" + name)

        ax1.imshow(image, cmap='gray')
        ax1.set_title(name+": \nGray - " + metric)

        ax2.imshow(np.log(abs(f_s)), cmap='gray')   # QUESTION: why log?
        ax2.set_title(name+": \nFourier - " + metric)

        ax3.imshow(img_i, cmap='gray')
        ax3.set_title(name+": \nInverse Fourier - " + metric)

    @staticmethod  # subplots
    def regular_all(image_matrix, filter_im, edge_matrix, name):

        fig, (ax1, ax2, ax3) = plt.subplots(nrows=1, ncols=3, figsize=(13, 5), num="Q.Plot.regular_all"+name)
        ax1.set_title(name+": image_matrix")
        ax2.set_title(name+": filter_im")
        ax3.set_title(name+": edge_matrix")

        ax1.imshow(image_matrix, cmap='hot')
        ax2.imshow(filter_im, cmap='hot')
        ax3.imshow(edge_matrix, cmap='hot')

    @staticmethod # subplots
    def edge_detect(matrix, blur_matrix, ima_matrix, edge_matrix, edge_matrix_laplace, speed_mask, maskon=None, info=""):

        fig, ((ax1, ax2, ax3), (ax4, ax5, ax6)) = plt.subplots(nrows=2, ncols=3, num="Q.Plot.edge_detect  -  "+info)

        ax1.imshow(matrix, cmap='hot')
        ax1.set_title("original - raw")

        ax2.imshow(blur_matrix, cmap='hot')
        ax2.set_title("original - blur")

        ax3.imshow(ima_matrix, cmap='hot')
        ax3.set_title(info)

        ax4.imshow(edge_matrix_laplace, cmap='hot')
        ax4.set_title("edges - laplace")

        #ax5.imshow(edge_matrix, cmap='hot')
        #ax5.set_title("edges - directional")

        if maskon is not None:
            ax5.imshow(maskon, cmap='hot')
            ax5.set_title("mask on filter")

        ax6.imshow(speed_mask, cmap='hot')
        ax6.set_title("binary mask")

    @staticmethod # subplots
    def subplots_img_2(dimX, dimY, first_half_img, second_half_img, combined_no_flip_img, combined_with_flip_img, second_half_flipped_img):

        fig, ((ax1, ax2, ax3), (ax4, ax5, ax6)) = plt.subplots(nrows=2, ncols=3, num="Q.Plot.subplots_img_2")

        ax1.imshow(first_half_img, cmap='hot', interpolation='none',
                   extent=[1, dimX, dimY, 1])  # [xmin (left), xmax (right), ymin (bottom), ymax (top)]
        ax1.set_title("First no flip")

        ax2.imshow(second_half_flipped_img, cmap='hot', interpolation='none', extent=[1, dimX, dimY, 1])
        ax2.set_title("Second with flip")

        ax3.imshow(combined_with_flip_img, cmap='hot', interpolation='none', extent=[1, dimX, dimY, 1])
        ax3.set_title("=> Combined")
        #
        ax4.imshow(first_half_img, cmap='hot', interpolation='none', extent=[1, dimX, dimY, 1])
        ax4.set_title("First no flip")

        ax5.imshow(second_half_img, cmap='hot', interpolation='none', extent=[1, dimX, dimY, 1])
        ax5.set_title("Second no flip")

        ax6.imshow(combined_no_flip_img, cmap='hot', interpolation='none', extent=[1, dimX, dimY, 1])
        ax6.set_title("=> Combined")

    @staticmethod # subplots
    def subplots_compare_flip(dimX, dimY, combined_no_flip_img, combined_with_flip_img, titles="", fig_title=""):

        fig, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, num="Q.Plot.subplots_compare_flip"+fig_title)

        ax1.imshow(combined_with_flip_img, cmap='hot', interpolation='none', extent=[1, dimX, dimY, 1])
        ax1.set_title(titles[1])

        ax2.imshow(combined_no_flip_img, cmap='hot', interpolation='none', extent=[1, dimX, dimY, 1])
        ax2.set_title(titles[0])

    @staticmethod # subplots
    def compare_noise_full_countrate(raw_countrate, filtered_countrate):

        fig, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, num="Q.Plot.compare_noise_full_countrate")

        ax1.plot(raw_countrate)
        ax1.set_title("Raw Countrate")

        ax2.plot(filtered_countrate)
        ax2.set_title("Noise Filtered Countrate")

    @staticmethod # subplots
    def compare_smoothing(course_matrix, smooth_matrices, titles):

        #fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4)
        fig, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, num="Q.Plot.compare_smoothing")

        ax1.imshow(np.array(course_matrix), cmap='hot')
        ax1.set_title("original")

        ax2.imshow(np.array(smooth_matrices[0]), cmap='hot')
        ax2.set_title(titles[0])

        """ax3.imshow(np.array(smooth_matrices[1]), cmap='hot')
        ax3.set_title(titles[1])
        
        ax4.imshow(np.array(smooth_matrices[2]), cmap='hot')
        ax4.set_title(titles[2])"""

    @staticmethod # subplots
    def test_value_filters(matrix, lower_thresh, upper_thresh, upper_val, noise=0, m=0, num=""):

        low_filter_matrix = Process.low_filter(matrix=np.array(matrix), lower_thresh=lower_thresh, lower_val=0)
        binary_filter_matrix = Process.binary_filter(matrix=np.array(matrix), thresh=lower_thresh, low=0, high=1)
        high_filter_matrix = Process.high_filter(matrix=np.array(matrix), upper_thresh=upper_thresh, upper_val=upper_val)

        high_filter_matrix1 = Process.high_filter(matrix=np.array(matrix), upper_thresh=noise, upper_val=noise+1)
        high_filter_matrix2 = Process.high_filter(matrix=np.array(matrix), upper_thresh=noise, upper_val=m)
        high_filter_matrix3 = Process.high_filter(matrix=np.array(matrix), upper_thresh=m, upper_val=m)

        fig, ((ax1, ax2, ax3), (ax4, ax5, ax6)) = plt.subplots(nrows=2, ncols=3, num=f"Q.Plot.test_value_filters - (low={lower_thresh}, high={upper_thresh}, val={upper_val})"+num)

        ax1.imshow(np.array(low_filter_matrix), cmap='hot', interpolation='none')
        ax2.imshow(np.array(high_filter_matrix), cmap='hot', interpolation='none')
        ax3.imshow(np.array(binary_filter_matrix), cmap='hot', interpolation='none')
        ax1.set_title("Low filter")
        ax2.set_title("High filter")
        ax3.set_title("Binary Mask")

        ax4.imshow(np.array(high_filter_matrix3), cmap='hot', interpolation='none')
        ax5.imshow(np.array(high_filter_matrix2), cmap='hot', interpolation='none')
        ax6.imshow(np.array(high_filter_matrix1), cmap='hot', interpolation='none')
        ax4.set_title(f"High filter:   thresh={round(m)}, val={round(m)}")
        ax5.set_title(f"High filter:   thresh={round(noise)}, val={round(m)}")
        ax6.set_title(f"High filter:   thresh={round(noise)}, val={round(noise+1)}")

        return low_filter_matrix, high_filter_matrix, binary_filter_matrix

    @staticmethod
    def refine_image_subplots(filtered_adjusted_matrix, raw_adjusted_matrix, img_no_flip, img_with_flip, const):

        for i, matrix in enumerate([filtered_adjusted_matrix, raw_adjusted_matrix, img_no_flip, img_with_flip]):
            kernels = ['gauss55']  # ['gauss33', 'gauss55']
            for k in kernels:
                #   BLUR BEFORE FILTER:
                fig, ((ax1, ax2, ax3, ax4), (ax5, ax6, ax7, ax8)) = plt.subplots(nrows=2, ncols=4,num="Blur Before Filter - " + k + "Blur Before Filter " + str(i))

                ax1.imshow(matrix, cmap='hot')
                ax1.set_title("og")
                ax1.axis("off")

                blur_matrix = Process.convolver(image=np.array(matrix), kernel=k, iterations=const["trans_iter"])
                ax2.imshow(blur_matrix, cmap='hot')
                ax2.set_title("og -> blur")
                ax2.axis("off")

                blur_low_matrix = Process.low_filter(matrix=np.array(blur_matrix), lower_thresh=const["noise"], lower_val=0)
                ax3.imshow(blur_low_matrix, cmap='hot')
                ax3.set_title("og -> blur -> low")
                ax3.axis("off")

                blur_low_binary_matrix = Process.binary_filter(blur_low_matrix, 0, low=0, high=1)
                ax4.imshow(blur_low_binary_matrix, cmap='hot')
                ax4.set_title("og -> blur -> low -> binary ")
                ax4.axis("off")

                binary_matrix = Process.binary_filter(matrix=np.array(matrix), thresh=const["noise"], low=0, high=1)
                ax5.imshow(binary_matrix, cmap='hot')
                ax5.set_title("og -> binary")
                ax5.axis("off")

                blur_low_matrix = Process.low_filter(matrix=np.array(blur_matrix), lower_thresh=const["noise"], lower_val=0)
                ax6.imshow(blur_low_matrix, cmap='hot')
                ax6.set_title("og -> blur -> low")
                ax6.axis("off")

                blur_low_binary_conv_matrix = binary_matrix * blur_low_matrix
                ax7.imshow(blur_low_binary_conv_matrix, cmap='hot')
                ax7.set_title("(og -> binary)*(og -> blur -> low)")
                ax7.axis("off")

                blur_low_binary_conv_binary_matrix = Process.binary_filter(blur_low_binary_conv_matrix, 0, low=0, high=1)
                ax8.imshow(blur_low_binary_conv_binary_matrix, cmap='hot')
                ax8.set_title("((og -> binary)*(og -> blur -> low)) \n-> binary")
                ax8.axis("off")

                # blur_low_edges_matrix = Q.Process.edge_detection(i_matrix=blur_low_matrix, new_option=True)  # new_option = (True->laplace), (False->4 sides)
                # ax_.imshow(blur_low_edges_matrix, cmap='hot')
                # ax_.set_title("raw -> blur -> low -> edges")

                """#pass_matrix_bbf = blur_matrix_bbf # ????
                #name = "bbf "+k
                #Q.Plot.regular_all(ima_matrix_bbf, pass_matrix_bbf, edge_matrix_bbf, name)
                #Q.Plot.fourier_all([ima_matrix_bbf, pass_matrix_bbf, edge_matrix_bbf], ["raw image", "convolver filtered", "edge detected"], name, subplts=False)"""

    @staticmethod
    def filter_vs_raw_subplots(filtered_adjusted_matrix, raw_adjusted_matrix, const, noise):
        iterNames = ["filtered_adjusted_matrix", "raw_adjusted_matrix"]
        adjusted_matrices = [filtered_adjusted_matrix, raw_adjusted_matrix]
        for i in range(2):
            iterName = iterNames[i]
            adjusted_matrix = adjusted_matrices[i]
            # -----

            # create speed adjusted mask if we are using noise filter:
            speed_mask = Process.binary_filter(np.array(adjusted_matrix), thresh=noise, low=const["noise_saturation"], high=1)

            blur_matrix = Process.convolver(image=np.array(adjusted_matrix), kernel=const["ker"], iterations=const["trans_iter"])
            noise_blur_filtered_adjusted_matrix = blur_matrix * speed_mask

            # edge_matrix = Q.Process.edge_detection(i_matrix=adjusted_matrix, new_option=False)
            # edge_matrix_laplace = Q.Process.edge_detection(i_matrix=adjusted_matrix, new_option=True)
            edge_matrix = Process.edge_detection(i_matrix=speed_mask, new_option=False)
            edge_matrix_laplace = Process.edge_detection(i_matrix=speed_mask, new_option=True)

            # -------------------------
            fig, ((ax1, ax2, ax3), (ax4, ax5, ax6)) = plt.subplots(nrows=2, ncols=3, num="Q.Plot.edge_detect " + iterName)

            ax1.imshow(adjusted_matrix, cmap='hot')
            ax1.set_title(iterName)

            # ax4.imshow(np.array(filtered_adjusted_matrix), cmap='hot')
            # ax4.set_title("filtered_adjusted_matrix")

            ax3.imshow(edge_matrix_laplace, cmap='hot')
            ax3.set_title("edges laplace - from mask")

            ax2.imshow(blur_matrix, cmap='hot')
            ax2.set_title(f"blur_matrix: blur->({iterName})")

            ax5.imshow(noise_blur_filtered_adjusted_matrix, cmap='hot')
            ax5.set_title("blur_matrix * mask with tolerance")

            ax4.imshow(edge_matrix, cmap='hot')
            ax4.set_title("edges directional - from mask")

            ax6.imshow(np.array(speed_mask), cmap='hot')
            ax6.set_title("noise mask")
            # -------------------------


# -------- UNUSED FUNCTIONS --------

class Unknown_or_Unused:

    def gauss_metrics(self, x, y, index_ref):
        #Fits a gaussian curve to the data and then pics out, ToF, Peak, Intensity
        # NOTE: inherited from previous version of library

        supermodel = fitModels.ConstantModel() + fitModels.GaussianModel()
        guess = self.gauss_guess(x, y)
        binsize = x[1] - x[0]
        amp = guess['amp']
        center = guess['center']
        sigma = guess['sigma']
        params = supermodel.make_params(amplitude=amp, center=center, sigma=sigma, c=5)
        result = supermodel.fit(y, params=params, x=x)
        sigma = result.params['sigma'].value
        height = result.params['height'].value
        intensity = result.params['amplitude'].value

        tof = self.calcTof(binsize*index_ref, center) #time of flight from reference time to where the peak is
        return tof, intensity, height

    @staticmethod
    def i_matrix(resultdict, metric):
        """ Creates a matrix with the metric values over the coordinate system """
        x = []
        y = []
        inten = []
        # mask = []
        metr = metric  # the metric from analysis to make an image of

        for p in resultdict:  # MS: walk through dictionary
            x.append(p[0])  # i values
            y.append(p[1])  # j values
            e = resultdict[p][metric]
            inten.append(e)

            # Do we need this??
            # if e < max_value and e != 0:
            #     inten.append(e)
            #     mask.append(0) #MS: dont understand
            # else:
            #     inten.append(0) #MS: dont understand
            #     mask.append(1) #MS: dont understand

        xdim = int(np.max(x)) + 1
        ydim = int(np.max(y)) + 1

        inten = np.array(inten)
        metricmatrix = inten.reshape(xdim, ydim)  # Creates a symmetric matrix of the metric data
        norm_metricmatrix = metricmatrix * 255 / np.max(metricmatrix)  # normalize metric values to between pixel values of 0-255

        return metricmatrix, norm_metricmatrix, metr

    @staticmethod
    def calcTof(t_ref, t_signal): #calculates the differnce between times between peak time and reference time in picoseconds
        # NOTE: inherited from previous version of library
        return t_signal-t_ref

    @staticmethod
    def integral(y, peak_value): #Function to extract intensity, y = histogram
        # NOTE: inherited from previous version of library

        peak_index = np.where(y == peak_value)[0][0] #Get the index for the max value in the array of count values (in the histogram of 6250 values)
        n = 10 #half interval
        s = 0 #Integral sum
        for j in range(peak_index-n, peak_index+n): #Interval to integrate over
            try:
                s+=y[j] #Summation of the count staples over the interval
            except IndexError:
                print("Integral failed: Maybe check this out")
                break
        return s

    def peak_metrics(self, x, y, index_ref): #Function to extract peak, height and intensity from individual histograms for each mirror position
        # NOTE: inherited from previous version of library

        binsize = x[1]-x[0]
        height = np.amax(y) #find the peak
        intensity = self.integral(y, height) #integrate counts over an interval
        tof = self.calcTof(binsize*index_ref, binsize*np.where(y == height)[0][0]) #time of flight from reference time to where the peak is
        return tof, intensity, height

    @staticmethod
    def FWHM(y, peak_index, binsize):
        # NOTE: inherited from previous version of library

        peak = y[peak_index]
        half_peak = peak/2
        r1 = 0  # placeholder /J
        r2 = 0  # placeholder /J
        i = 1
        run_up, run_down = True, True
        while run_up or run_down:
            try:
                upper = y[peak_index+i]
                lower = y[peak_index-i]

                if upper <= half_peak and run_up:
                    r1 = peak_index + i
                    run_up = False

                if lower <= half_peak:
                    r2 = peak_index - i
                    run_down = False

                i += 1

            except IndexError:
                return 25
        if r1 == 0 or r2 == 0:
            print("r1 or r2 is 0, check if functions works correctly /J")
        FW = (r1-r2)*binsize
        return FW

    def gauss_guess(self, x, y):
        # NOTE: inherited from previous version of library

        binsize = x[1]-x[0]
        peak = np.max(y)
        peak_index = np.where(y == np.max(y))[0][0]
        center = x[peak_index]
        sigma = self.FWHM(y, peak_index, binsize)/2.355
        amp = peak*(sigma*np.sqrt(2*np.pi))
        d = {'amp': amp, 'center': center, 'sigma': sigma}
        return d

    @staticmethod
    def countrate_analysis(countrate_matrix, dimX):
        # NOTE: replaced by new segmented function

        img_matrix = []

        for i in range(dimX):
            row = countrate_matrix[i]
            flipped_row = row.copy()
            flipped_row = np.flip(flipped_row)

            row += flipped_row

            row = row[0:100]
            img_matrix.append(row)

        return img_matrix

    @staticmethod
    def eta_analysis(file, eta_engine):
        # NOTE: replaced by new segmented function

        print('Starting ETA analysis')
        cut = eta_engine.clips(Path(file))
        result = eta_engine.run({"timetagger1": cut}, group='qutag')
        print('Finished ETA analysis')
        return result

    @staticmethod
    def heatmap(i_matrix, metric, filter, nor, iter, show=False, log=True):
        # NOTE: inherited from previous version of library
        # FIXME: maybe.

        if log == True:
            norm = LogNorm()
        else:
            norm = None

        plt.figure(num="Heatmap", figsize=(10, 8), dpi=150)
        plt.imshow(i_matrix, cmap='hot', norm=norm)   # NOTE: previously:  cmap = cm.brg
        plt.colorbar()

        savepath = metric+"_"+nor+"_"+filter+"_"+"iter_"+str(iter)+".png"
        #plt.savefig(savepath)
        if show:
            plt.show()
        #plt.close()


class GraveYard:  # older versions of functions that are not ready to be let go of

    @staticmethod
    def eta_segmented_analysis(timetag_file, ch_sel, eta_engine, bins, dimY, flip): #, noise=0):
        print("Starting Analysis")

        if bins > dimY:
            compress = True  # NOTE: this is if bins >> dimX, and we want a quadratic even pixel size
        else:
            compress = False  # TODO: need to test if "else -> compress" works!

        # ------ETA PROCESSING-----
        pos = 0
        context = None
        run_flag = True
        list_countrate = []
        filtered_countrate = []
        image_combined_no_flip = []
        image_combined_with_flip = []

        while run_flag:
            row, pos, context, run_flag = Data.get_row_from_eta(eta_engine, timetag_file, pos, context, ch_sel, run_flag)
            if pos is None:
                print("No new elements left to extract from ETA")
                break

            # ----

            combined_no_flip = list(np.array(row[:int(bins / 2)]) + np.array(row[int(bins / 2):]))
            combined_flipped = list(np.array(row[:int(bins / 2)]) + np.array(np.flip(row[int(bins / 2):])))

            if compress:
                compressed_no_flip, _ = Process.compress_bins_into_pixels(bins, pixY=dimY, row=combined_no_flip)
                compressed_with_flip, _ = Process.compress_bins_into_pixels(bins, pixY=dimY, row=combined_flipped)
                image_combined_no_flip.append(compressed_no_flip)
                image_combined_with_flip.append(compressed_with_flip)

            else:
                image_combined_no_flip.append(combined_no_flip)
                image_combined_with_flip.append(combined_flipped)

            # add to full countrate list
            list_countrate += list(row)

            _, temp1 = Process.compress_bins_into_pixels(bins, pixY=dimY, row=row[:int(bins / 2)])
            _, temp2 = Process.compress_bins_into_pixels(bins, pixY=dimY, row=row[int(bins / 2):])
            filtered_countrate += list(temp1)
            filtered_countrate += list(temp2)

        print("All elements processed.\nAnalysis Finished")
        return list_countrate, filtered_countrate, image_combined_no_flip, image_combined_with_flip

    @staticmethod   # Updated version called: "get_velocity_bin_lists"
    def scan_path(amp_Y, y_freq, base_bins, base_binsize):
        # NOTE: inherited from previous version of library
        realtime_list = np.arange(base_bins) * base_binsize  # Create list with "real" time (unit: ps)  --> time = step * bin-size

        y_value_list = []         # create a list of y-values for each timestep (unit current)
        y_velocity_list = []      # create a list of velocities for each timestep (unit current/time)
        for t_curr in realtime_list:
            y_value_list.append(Function.y_value(amp_Y, y_freq, t_curr))
            y_velocity_list.append(Function.y_velocity(amp_Y, y_freq, t_curr))

        # create a list of y-value contributions for each time-step. Calculated as y-value = velocity * base_binsize
        y_velocity_bin_list = np.array(y_velocity_list) * base_binsize  # rescale velocity list: y_velocity_list[i] * base_binsize /J

        return list(y_velocity_bin_list)  # , realtime_list, yvaluelist, velocitylist, velocitybinlist

    @staticmethod
    def full_compress_bins_into_pixels(bins, dimY, first_half, second_half, second_half_flipped, combined_no_flip, combined_flipped):
        first_half_list = []
        second_half_list = []
        second_half_flipped_list = []
        combined_no_flip_list = []
        combined_flipped_list = []

        extra = int(round(bins / (2 * dimY)))
        print(extra)
        # sum values in bins to make up one equally sized pixel
        for i in range(dimY):  # NOTE: here n_sweeps = 2
            # if (bins = 20000)  --> (bins when combined two sweeps = ) and  (dimY = 100)  --> bins = dimY*200  --> we need to compress every 200 values into one

            # NOTE: These are split into half periods
            first_half_list.append(sum(first_half[i * extra:(i + 1) * extra]))
            second_half_list.append(sum(second_half[i * extra:(i + 1) * extra]))
            second_half_flipped_list.append(sum(second_half_flipped[i * extra:(i + 1) * extra]))

            combined_no_flip_list.append(sum(combined_no_flip[i * extra:(i + 1) * extra]))
            combined_flipped_list.append(sum(combined_flipped[i * extra:(i + 1) * extra]))

        return first_half_list, second_half_list, second_half_flipped_list, combined_no_flip_list, combined_flipped_list

    @staticmethod
    def high_pass_filter(matrix, threshold, dimX, dimY, strict=False):
        """Set pixel high pass filter"""
        # NOTE: inherited from previous version of library
        # FIXME: yes, simplify.

        filtered_matrix = np.array(matrix)
        print("Pixels where counts are above the threshold " + str(threshold))
        #arglist = np.argwhere(filtered_matrix > threshold)
        #for i in range(len(arglist)):
        #    print("position: " + str(arglist[i]) + ", value: " + str(filtered_matrix[arglist[i][0], arglist[i][1]]))
        for i in range(dimX):
            for j in range(dimY):
                #if threshold < filtered_matrix[i, j] < (threshold * 1.2):
                #    filtered_matrix[i, j] = 100  # threshold
                if strict:
                    pass
                    """if 600 == filtered_matrix[i, j]:
                        filtered_matrix[i, j] = 1000  # threshold
                    else:
                        filtered_matrix[i, j] = 0  # threshold"""

                else:
                    if threshold < filtered_matrix[i, j]:
                        filtered_matrix[i, j] = 200  # threshold
        return filtered_matrix

    @staticmethod
    def low_pass_filter(matrix, threshold, dimX, dimY):
        """Set pixel high pass filter"""
        filtered_matrix = np.array(matrix)

        for i in range(dimX):
            for j in range(dimY):
                if filtered_matrix[i, j] <= threshold:
                    filtered_matrix[i, j] = 0
        return filtered_matrix

    @staticmethod
    def low_high_pass_filter(matrix, threshold, dimX, dimY, use_lp=False, use_hp=False):
        """Filter high and low pixel values"""
        filtered_matrix = np.array(matrix)

        low = 0
        high = 2 * threshold  # this ensures we don't accidentally filter high values at some point

        # replace values with "low" that fulfill condition "filtered_matrix < threshold"
        high_filtered_matrix = np.where(filtered_matrix <= threshold, low, filtered_matrix)

        # replace values with "high" that fulfill condition "filtered_matrix >= threshold"
        low_filtered_matrix = np.where(filtered_matrix > threshold, high, filtered_matrix)

        # np.where({condition to test truth}, {value if True}, {value if False})
        both_filtered_matrix = np.where(filtered_matrix > threshold, high, low)

        """
        if use_hp and use_lp:
            for i in range(dimX):
                for j in range(dimY):
                    if filtered_matrix[i, j] > threshold:
                        filtered_matrix[i, j] = 200
                    elif filtered_matrix[i, j] <= threshold:
                        filtered_matrix[i, j] = 0

        elif use_hp:
            for i in range(dimX):
                for j in range(dimY):
                    if threshold < filtered_matrix[i, j]:
                        filtered_matrix[i, j] = 200  
        elif use_lp:
            for i in range(dimX):
                for j in range(dimY):
                    if filtered_matrix[i, j] <= threshold:
                        filtered_matrix[i, j] = 0"""

        return filtered_matrix

    @staticmethod
    def old_try_noise_filter(matrix, countrate, noise_tolerance, dimX, dimY):
        noise = Process.get_noise_value(matrix, noise_tolerance)
        filtered_matrix = np.array(matrix)
        noise_mask = np.ones((dimX, dimY))  # (rows, cols)
        print("test", len(filtered_matrix[0]), len(filtered_matrix))

        for i in range(len(filtered_matrix)):
            for j in range(len(filtered_matrix[0])):
                if filtered_matrix[i, j] < noise:
                    filtered_matrix[i, j] = 0
                    noise_mask[i, j] = 0

        return filtered_matrix, noise_mask, countrate

    @staticmethod
    def subplots_img_1(first_half_img, second_half_img, half_combined_no_flip, half_combined_with_flip, first_half_img_corrected, second_half_img_corrected):

        fig, ((ax1, ax2, ax3), (ax4, ax5, ax6)) = plt.subplots(nrows=2, ncols=3, num="Q.Plot.subplots_img_1")

        ax1.imshow(half_combined_with_flip, cmap='hot')
        ax1.set_title("Combined with flip")

        ax4.imshow(half_combined_no_flip, cmap='hot')
        ax4.set_title("Combined no flip")
        # ax4.get_xaxis().set_visible(False)
        # ax4.get_yaxis().set_visible(False)

        ax2.imshow(first_half_img, cmap='hot')
        ax2.set_title("First original")

        ax3.imshow(second_half_img, cmap='hot')
        ax3.set_title("Second original")

        ax5.imshow(first_half_img_corrected, cmap='hot')
        ax5.set_title("First correct <-")

        ax6.imshow(second_half_img_corrected, cmap='hot')
        ax6.set_title("Second correct ->")

    @staticmethod
    def final_transforms_and_plots(matrix, name, kernel, iter, thresh):

        name = "ker: " + name
        blur_before_filter = False
        blur_for_edge = False

        print("Pass filter thresh =", thresh)

        if blur_for_edge:
            if blur_before_filter:
                blur_matrix = Process.convolver(image=np.array(matrix), kernel=kernel, iterations=iter)
                pass_matrix = Process.low_filter(matrix=np.array(blur_matrix), lower_thresh=thresh, lower_val=0)  # pass_matrix = pass_filters(blur_matrix, thresh=thresh)
                ima_matrix = pass_matrix
            else:
                pass_matrix = Process.low_filter(matrix=np.array(matrix), lower_thresh=thresh, lower_val=0)  # pass_matrix = pass_filters(matrix, thresh=thresh)
                blur_matrix = Process.convolver(image=pass_matrix, kernel=kernel, iterations=iter)
                pass_matrix = Process.low_filter(matrix=np.array(blur_matrix), lower_thresh=thresh, lower_val=0)  # pass_matrix = pass_filters(blur_matrix, thresh=thresh)  # NOTE: added an extra low filter
                ima_matrix = pass_matrix

        else:
            pass_matrix = Process.low_filter(matrix=np.array(matrix), lower_thresh=thresh, lower_val=0)  # pass_matrix = pass_filters(np.array(matrix), thresh=thresh)
            ima_matrix = pass_matrix
            blur_matrix = Process.convolver(image=np.array(matrix), kernel=kernel, iterations=iter)

        edge_matrix = Process.edge_detection(i_matrix=ima_matrix, new_option=False)
        edge_matrix_laplace = Process.edge_detection(i_matrix=ima_matrix, new_option=True)


        # Create plots:
        Plot.edge_detect(matrix, blur_matrix, ima_matrix, edge_matrix, edge_matrix_laplace, speed_mask=np.zeros((100,100)))
        # plt.show()
        # Plot.regular_all(ima_matrix, pass_matrix, edge_matrix, name)
        # plt.show()
        # Plot.fourier_all([ima_matrix, pass_matrix, edge_matrix], ["raw image", "convolver filtered", "edge detected"], name, subplts=False)
        # plt.show()




