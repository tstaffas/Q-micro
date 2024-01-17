import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename, askdirectory
import time
import serial
#from serial.tools import list_ports
from datetime import date, datetime
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
# from matplotlib import style
# from matplotlib.backend_bases import key_press_handler

import threading   #? maybe remove
import webbrowser  # ??

# Plotly:
#import plotly.graph_objs as go
#from dash import Dash, dcc, html  # , #Input, Output
#from dash.dependencies import Output, Input

# Logger:
import logging
import datetime

# from WebSQControl import WebSQControl

# Packages for ETA backend
#import json
#import etabackend.eta  # Available at: https://github.com/timetag/ETA, https://eta.readthedocs.io/en/latest/

import os
from pathlib import Path

# --------
import time
from labjack import ljm
import socket
import pickle


# from liquid_lens_lib import OptoLens
# import sys  # unsure what we thought we needed this for


# ---------------------- USEFUL LINKS ------------------------
# Buffer stream addresses
# https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/32-stream-mode-t-series-datasheet/#section-header-two-kmwnd
# ...

# ------------------------------------------------------------
# TODO LATER:
#   > check max frequency for sine values sent from buffer (given that we want to send out 256 values in half a period)
#       -> if max frequency allows it, our current upper limit for frequency is 500 Hz. (T/2 >= 1ms, T >= 2ms, 1/f >= 2/1000 s, 500 >= f)
#   > write a "read_me" file with information and instructions
#   > make a nice, simple, little interactive window for users to choose their settings (to keep code safe)
#       -> have it display the max and min of different values (maybe with a slider), and also print out some logs ... *fancy!*
#   > consider if we need to do something about "drifting" based on temperature
#
# ------------------------------------------------------------
# TODO SOONER (IMPROVEMENTS):
#   > check source code on "ljm_stream_util.prepareForExit()" and see if we can improve our exit function
#   > clean up / improve function "socket_connection()"
#   > clean up comments, remove unused code
#   > double check that all error checks are still working
#   > double check everything we define in "get_scan_parameters()"
#   > read back what our stream scan rate is

# ------------------------------------------------------------
#   > fix a nicer solution to "calc_wait_delays", with variables (maybe %)
#       -> calculate and check that it is correct! (maybe plot and sum up to a period?)
#       -> when complete, move out of function and directly into "get_scan_params()"
#       -> sub in the wait delay variables in function: "add_wait_delay()"
#           --> CHECK THAT RANGE INT ROUNDING DOESN'T MESS WITH TOTAL DELAY
#           --> COUNT OR MAKE "int(self.step_delay / 0.1)" something we use to calculate the remaining delay
# ------------------------------------------------------------

# UPDATED 2 nov 2023
#    if len(self.step_values) == self.step_dim

# TODO:
#  - warm up
#  - liquid lens "scan_z"   maybe with n number of frames per z level


# CORE OF CODE:
def main():
    global t7, gui, eta
    # 1) Initialize

    t7 = T7()

    gui = GUI()

    #eta = ETA()  # note move this to be initialized when starting a new scan

    try:
        gui.root.after(500, gui.scanning)  # After 1 second, call scanning
        gui.root.mainloop()

    except KeyboardInterrupt:
        gui.logger_box.module_logger.info("ERROR: Keyboard Interrupt")
        raise

    except SystemExit:
        gui.logger_box.module_logger.info("ERROR: System Exit")
        raise

    except tk.EXCEPTION:
        gui.logger_box.module_logger.info("ERROR: tkinter exception")
        raise

    except serial.SerialException:
        gui.logger_box.module_logger.info("ERROR: serial exception")
        raise

    except:
        # reset if script encounters an error and exit out
        gui.logger_box.module_logger.info("ERROR: (some default error)")
        raise

    finally:
        print('------\nFINALLY:')
        t7.close_labjack_connection(printlog=False)
        gui.close(printlog=False)  # Close all external connections
        #t7.socket_connection(shutdown_server=True)  # NOTE TODO, REMOVE AFTER DEMO

    # TODO: MOVE TO RIGHT PLACES
    #t7.reset_scan_vars()  # call before starting new scan
    #t7.main_galvo_scan()  # call to start new scan  (it will first check all value to see if they are ok)


class GUI:

    def __init__(self):

        # Create and configure the main GUI window
        self.init_window()

        # define global variables
        self.init_parameters()
        self.x = None
        self.y = None
        self.z = None

        # Create and place tabs frame on window grid
        self.init_fill_tabs()
        self.live_mode = True  # FIXME: add button to change this

    def init_window(self):
        self.root = tk.Tk()
        self.root.title("Quantum Microscope GUI")  # *Ghostly matters*
        #self.root.resizable(True, True)
        # self.root.config(background='#0a50f5')   # TODO figure out why colors don't work
        self.root.geometry('1200x900')

    def init_parameters(self):
        # TODO: CHECK WHAT WE CAN REMOVE!!!
        self.tabControl = None  # for plot we destoy occasionally
        self.data = []
        self.running = False  # this tracks if we are running a scan (collecting counts from detector)
        self.demo_connect = False  # temp for demo to check if we've actually connected to device
        self.current_file_name = None
        self.current_file_type = None
        self.current_file_path = None
        self.widgets = {}
        self.button_color = 'grey'  # default button colors
        self.port = tk.StringVar()  # note maybe change later when implemented
        self.params = {
            'nr_pixels': {'var': tk.IntVar(value=4), 'type': 'int entry', 'default': 4, 'value': [1, 2, 4]},
            'file_name': {
                'var': tk.StringVar(value=""),
                'type': 'str entry',
                'default': 'ToF_Bio_cap_10MHz_det1_marker_ch4_10.0ms_[2.1, 2.45, -1.4, -3.4]_100x100_231218.timeres',
                'value': ['ToF_terra_10MHz_det2_10.0ms_[2.1, 2.5, -3.2, -4.8]_100x100_231030.timeres',
                          'ToF_terra_10MHz_det2_1.0ms_[2.1, 3.9, -3.2, -4.8]_100x100_231102.timeres',
                          'ToF_terra_10MHz_det2_0.5ms_[2.1, 3.9, -3.2, -4.8]_100x100_231102.timeres']},
            # 'folder_name': {'var': tk.StringVar(),       'type': 'str entry', 'default': '',  'value': ['~/Desktop/GUI/Data1', '~/Desktop/GUI/Data2', '~/Desktop/GUI/Data3']},
            'eta_recipe': {'var': tk.StringVar(value=""), 'type': 'str entry',
                           'default': '3D_tof_swabian_marker_ch4.eta',
                           'value': ['3D_tof_swabian_marker_ch4.eta', 'lifetime_new_spectrometer_4_ch_lifetime.eta',
                                     'lifetime_det1_spectrometer_tof.eta']},
        }
        self.ch_bias_list = []
        self.ch_trig_list = []
        self.logger_box = None   # unsure if we should define it here at all

        # ANALYSIS PARAMS:
        #self.eta_recipe = tk.StringVar(value='Swabian_multiframe_recipe_bidirectional_segments_marker4_20.eta')  # value='C:/Users/vLab/Desktop/Spectra GUI  Julia/LIDAR GUI/Recipes/3D_tof_swabian_marker_ch4.eta')
        self.eta_recipe = tk.StringVar(value='Swabian_multiframe_recipe_bidirectional_segments_0.0.4.eta')  # value='C:/Users/vLab/Desktop/Spectra GUI  Julia/LIDAR GUI/Recipes/3D_tof_swabian_marker_ch4.eta')
        self.data_folder = tk.StringVar(value='K:/Microscope/Data/240116/')
        self.clue = tk.StringVar(value='digit6')
        self.bins = tk.IntVar(value=20000)  # bins*binssize = 1/frep [ps]
        self.ch_sel = tk.StringVar(value='h3')
        self.save_folder = tk.StringVar(value='/Analysis')   # where images, gifs and analysis is saved

        # SCAN PARAMS:
        #self.dimX = tk.IntVar(value=100)
        self.dimY = tk.IntVar(value=100)
        self.freq = tk.DoubleVar(value=5.0)
        self.nr_frames = tk.IntVar(value=1)
        self.ampX = tk.DoubleVar(value=0.3)  # --> step values between -0.3 and 0.3
        self.ampY = tk.DoubleVar(value=0.3)  # --> sine values between -0.3 and 0.3
        self.data_folder = tk.StringVar(value='/Users/juliawollter/Desktop/Microscope GUI/Data')
        self.data_file = tk.StringVar(value='digit6_sineFreq(1.0)_numFrames(10)_sineAmp(0.3)_stepAmp(0.3)_stepDim(100)_date(240114)_time(22h20m23s).timeres')

        # -----------

    def init_fill_tabs(self):

        # TABS STYLE
        style1 = ttk.Style()
        style1.theme_create("style1", parent="alt", settings={
            "TNotebook": {"configure": {"tabmargins": [0, 0, 0, 0]}},
            "TNotebook.Tab": {"configure": {"padding": [10, 10], "font": ('garamond', '11', 'bold')}, }})
        style1.theme_use("style1")
        TROUGH_COLOR = 'white'
        BAR_COLOR = 'blue'
        style1.configure("bar.Horizontal.TProgressbar", troughcolor=TROUGH_COLOR, bordercolor=TROUGH_COLOR,
                         background=BAR_COLOR, lightcolor=BAR_COLOR, darkcolor=BAR_COLOR)
        # style1.configure("green.Horizontal.TProgressbar", foreground='green', background='green')
        # style1.configure("red.Horizontal.TProgressbar", troughcolor='gray', background='red')  # progressbar!!

        # ----Create notebooks for multi tab window:----

        # ADD TABS TO MANAGER 2
        tabControl2 = ttk.Notebook(self.root)

        # LIVE SCAN TAB: (but not live yet!!!!)
        live_tab = ttk.Frame(tabControl2)
        tk.Label(live_tab, text='Scan Settings', font=('', 15), width=20).grid(row=0, column=0, sticky="news", padx=0, pady=0)

        tk.Button(live_tab, text="Disconnect", command=t7.close_labjack_connection, activeforeground='blue',
                  highlightbackground=self.button_color).grid(row=0, column=1, sticky='news', padx=0, pady=0)

        #   Data acquisition (pre scan)
        self.choose_scan_configs_widget(live_tab).grid(row=1, column=0, columnspan=2, sticky="news", padx=2, pady=0)

        # Data processing (post scan)
        self.choose_analysis_configs_widget(live_tab).grid(row=2, column=0, columnspan=2, sticky="news", padx=0, pady=0)  # in sub frame

        # Start scan button
        self.start_scan_widget(live_tab).grid(row=3, column=0, columnspan=2, sticky="news", padx=2, pady=0)  # in sub frame

        # Logged information:
        self.log_scan_widget(live_tab).grid(row=4, column=0, columnspan=2, sticky="new", padx=2, pady=0)  # in sub frame

        self.plot_analysis_widget(live_tab).grid(row=0, column=2, rowspan=10, sticky="new", padx=2, pady=0)  # in sub frame

        tabControl2.add(live_tab, text='New Scan')
        # ----

        tabControl2.grid(row=0, column=0, sticky='nesw', pady=5)

    # ---------------

    @staticmethod
    def add_to_grid(widg, rows, cols, sticky, columnspan=None):
        for i in range(len(widg)):
            if columnspan:
                widg[i].grid(row=rows[i], column=cols[i], sticky=sticky[i], padx=0, pady=0, columnspan=columnspan[i])
            else:
                widg[i].grid(row=rows[i], column=cols[i], sticky=sticky[i], padx=0, pady=0)

    def choose_scan_configs_widget(self, tab):

        def suggest_name():

            filename = f'{variables["info"]["var"].get()}_' \
                   f'sineFreq({variables["frequency"]["var"].get()})_' \
                   f'numFrames({variables["nr frames"]["var"].get()})_' \
                   f'sineAmp({variables["amp X"]["var"].get()})_' \
                   f'stepAmp({variables["amp Y"]["var"].get()})_' \
                   f'stepDim({variables["dim Y"]["var"].get()})_' \
                   f'date({date.today().strftime("%y%m%d")})_' \
                   f'time({time.strftime("%Hh%Mm%Ss", time.localtime())}).timeres'

            variables['filename']['entry'].delete(0, tk.END)
            variables['filename']['entry'].insert(0, filename)

        def open_folder():
            file = askdirectory()
            variables['save folder']['entry'].delete(0, tk.END)
            variables['save folder']['entry'].insert(0, file)

        def init_plot(show):
            ##---
            x_l = []
            y_l = []
            fig, ax = plt.subplots(1, 1, figsize=(3, 3))
            if show:
                ax.plot(x_l, y_l, 'b-')
                ax.set_axis_off()
                fig.canvas.draw_idle()  # updates the canvas immediately?
                plt_frame1, canvas1 = self.pack_plot(frm_misc, fig, toolbar=False)  # scatter
                plt_frame1.grid(row=1, column=3, rowspan=10, columnspan=10, sticky="news", padx=0, pady=0)

                tk.Button(frm_misc, text="plot path", command=plot_path, activeforeground='blue',
                          highlightbackground=self.button_color).grid(row=13, column=0, sticky='ew', padx=0, pady=0)

            return fig, ax

        def plot_path():
            step_vals = []  # y-vals

            step_size = (2 * variables["amp Y"]["var"].get()) / (variables["dim Y"]["var"].get() - 1)  # step size of our x values
            k = -1 * variables["amp Y"]["var"].get()
            for i in range(variables["dim Y"]["var"].get()):
                step_vals.append(round(k + t7.y_offset, 10))
                k += step_size

            x_min = - variables["amp X"]["var"].get() / 2
            x_max = variables["amp X"]["var"].get() / 2

            x_l = []
            y_l = []
            for j in range(0, len(step_vals), 2):
                x_l += [x_min, x_max, x_max, x_min]
                y_l += [step_vals[j], step_vals[j], step_vals[j+1], step_vals[j+1]]

            ax1.clear()
            ax1.set_axis_off()
            ax1.plot(x_l, y_l, 'b-')
            fig1.canvas.draw_idle()   # updates the canvas immediately?
            gui.logger_box.module_logger.info("Done plotting")

        def select_demo():
            if self.demo_mode.get() is True:
                self.diagnostics_mode.set(False)
                self.record_mode.set(False)
            else:
                self.record_mode.set(True)

        def select_record():
            if self.record_mode.get() is True:
                self.demo_mode.set(False)
            else:
                self.demo_mode.set(True)
                self.diagnostics_mode.set(False)

        def select_diagnostics():
            if self.diagnostics_mode.get() is True:
                self.record_mode.set(True)   # for diagnostics, we must be in record mode
            self.demo_mode.set(False)

        frm_misc = tk.Frame(tab, relief=tk.RAISED, bd=2)

        fig1, ax1 = init_plot(show=False)
        #----

        tk.Label(frm_misc, text='Acquisition', font=('', 15)).grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        file_lab_parts = []
        file_entry = []

        variables = {
            'info': {'entry': tk.Entry(frm_misc, bd=2, textvariable=self.clue, width=30), 'var': self.clue},
            'frequency': {'entry': tk.Entry(frm_misc, bd=2, textvariable=self.freq, width=15), 'var': self.freq},
            'nr frames': {'entry': tk.Entry(frm_misc, bd=2, textvariable=self.nr_frames, width=15), 'var': self.nr_frames},
            #'dim X':  {'entry': tk.Entry(frm_misc, bd=2, textvariable=self.dimX, width=15), 'var': self.dimX},
            'dim Y':     {'entry': tk.Entry(frm_misc, bd=2, textvariable=self.dimY, width=15), 'var': self.dimY},
            'amp X': {'entry': tk.Entry(frm_misc, bd=2, textvariable=self.ampX, width=15), 'var': self.ampX},
            'amp Y': {'entry': tk.Entry(frm_misc, bd=2, textvariable=self.ampY, width=15), 'var': self.ampY},
            'filename': {'entry': tk.Entry(frm_misc, bd=2, textvariable=self.data_file, width=15),  'var': self.data_file},
            #'save folder': {'entry': tk.Entry(frm_misc, bd=2, textvariable=self.data_folder, width=15), 'var': self.data_folder},
        }

        for i, label in enumerate(variables.keys()):
            file_lab_parts.append(tk.Label(frm_misc, text=label))
            file_entry.append(variables[label]['entry'])
            self.add_to_grid(widg=[file_lab_parts[i]], rows=[i + 1], cols=[0], sticky=["ew"])
            self.add_to_grid(widg=[file_entry[i]], rows=[i + 1], cols=[1], sticky=["ew"])  # FIXME  # TODO: CONTINUE HERE

        tk.Button(frm_misc, text="filename", command=suggest_name, activeforeground='blue',
                  highlightbackground=self.button_color).grid(row=7, column=0, sticky='ew', padx=0, pady=0)

        #tk.Button(frm_misc, text="save to", command=open_folder, activeforeground='blue',
        #          highlightbackground=self.button_color).grid(row=8, column=0, sticky='ew', padx=0, pady=0)

        self.record_mode = tk.BooleanVar(value=False)
        self.diagnostics_mode = tk.BooleanVar(value=False)
        self.demo_mode = tk.BooleanVar(value=True)

        tk.Checkbutton(frm_misc, text="Record Scan ", anchor="w", command=select_record, variable=self.record_mode, onvalue=True, offvalue=False).grid(row=9, column=0, sticky="ew", padx=0, pady=0)
        tk.Checkbutton(frm_misc, text="Diagnostics ", anchor="w", command=select_diagnostics, variable=self.diagnostics_mode, onvalue=True, offvalue=False).grid(row=9, column=1, sticky="ew", padx=0, pady=0)
        tk.Checkbutton(frm_misc, text="Demo/Offline", anchor="w", command=select_demo, variable=self.demo_mode, onvalue=True, offvalue=False).grid(row=10, column=0, sticky="ew", padx=0, pady=0)

        return frm_misc

    def choose_analysis_configs_widget(self, tab):

        def get_recipe():
            recipe = askopenfilename(filetypes=[("ETA recipe", "*.eta")])
            self.eta_recipe.set(recipe)
            variables['eta_recipe']['entry'].delete(0, tk.END)
            variables['eta_recipe']['entry'].insert(0, recipe)

        def open_datafile():
            file = askopenfilename(filetypes=[("Timeres", "*.timeres")])
            self.data_file.set(file)
            variables['file_name']['entry'].delete(0, tk.END)
            variables['file_name']['entry'].insert(0, file)

            # TODO: ALSO CHANGE OTHER VARIABLES
            update_variables(file)

        def open_folder():
            file = askdirectory()
            variables['save_folder']['entry'].delete(0, tk.END)
            variables['save_folder']['entry'].insert(0, file)

        def update_variables(file):
            # self.dimX =
            # self.dimY =
            # self.dimX =
            # self.dimX =
            # TODO: FIX REGEX LATER

            rect_str = ''
            xdim_str = ''
            ydim_str = ''

            rect_rng = []
            xdim_rng = []
            ydim_rng = []

            for i, char in enumerate(file):
                if char == '[':
                    rect_rng.append(i + 1)
                if char == ']':
                    rect_rng.append(i - 1)
                elif (file[i] == '_') and (file[i + 4] == 'x'):
                    xdim_rng = [i + 1, i + 3]
                elif (file[i] == 'x') and (file[i + 4] == '_'):
                    ydim_rng = [i + 1, i + 3]

            rect = file[rect_rng[0]:rect_rng[1] + 1]
            xdim = file[xdim_rng[0]:xdim_rng[1] + 1]
            ydim = file[ydim_rng[0]:ydim_rng[1] + 1]

            variables['rect']['entry'].delete(0, tk.END)
            variables['rect']['entry'].insert(0, rect)
            variables['dimX']['entry'].delete(0, tk.END)
            variables['dimX']['entry'].insert(0, xdim)
            variables['dimY']['entry'].delete(0, tk.END)
            variables['dimY']['entry'].insert(0, ydim)

            variables['rect']['var'].set(rect)
            variables['dimX']['var'].set(eval(xdim))
            variables['dimY']['var'].set(eval(ydim))

        def press_start_analysis():
            self.pb['value'] = 0
            self.root.update()  # testing

            # NOTE: HERE WE SHOULD START ANALYSIS?


        frm_misc = tk.Frame(tab, relief=tk.RAISED, bd=2)
        tk.Label(frm_misc, text='Analysis', font=('', 15)).grid(row=0, column=0, sticky="news", padx=0, pady=0)

        file_lab_parts = []
        file_entry = []

        variables = {
            'eta_recipe': {'entry': tk.Entry(frm_misc, bd=2, textvariable=self.eta_recipe, width=30), 'var': self.eta_recipe},
            'save_folder': {'entry': tk.Entry(frm_misc, bd=2, textvariable=self.save_folder, width=15),
                            'var': self.save_folder},

            'bins': {'entry': tk.Entry(frm_misc, bd=2, textvariable=self.bins, width=15), 'var': self.bins},
            'ch_sel': {'entry': tk.Entry(frm_misc, bd=2, textvariable=self.ch_sel, width=15), 'var': self.ch_sel},
        }

        for i, label in enumerate(variables.keys()):
            file_lab_parts.append(tk.Label(frm_misc, text=label))
            file_entry.append(variables[label]['entry'])
            self.add_to_grid(widg=[file_lab_parts[i]], rows=[i + 1], cols=[0], sticky=["ew"])
            self.add_to_grid(widg=[file_entry[i]], rows=[i + 1], cols=[1],
                             sticky=["ew"])  # FIXME  # TODO: CONTINUE HERE

        file_buts = [tk.Button(frm_misc, text="eta recipe", command=get_recipe, activeforeground='blue',
                               highlightbackground=self.button_color),
                     tk.Button(frm_misc, text="save folder", command=open_folder, activeforeground='blue',
                               highlightbackground=self.button_color)]
        self.add_to_grid(widg=file_buts, rows=[1, 2], cols=[0,0], sticky=["ew", "ew"])



        return frm_misc

    def update_progressbar(self, n=10):
        if self.pb['value'] < 100:
            self.pb['value'] = n + 1
            self.root.update()  # testing

    def scanning(self):

        if self.running:  # if start button is active
            #self.get_counts()  # saves data to self.data. note that live graph updates every second using self.data
            #self.save_data(mode="a")
            gui.logger_box.module_logger.info(".")
            pass
        self.root.after(500, self.scanning)  # After 1 second, call scanning

    def save_data(self, mode):
        data_str = []
        for row in self.data:
            vals = [str(int(x)) for x in row]
            data_str.append(' '.join(vals) + ' \n')
        with open("counts_file.txt", mode) as file:  # FIXME need to make sure that new scan => new/empty file
            file.writelines(data_str)  # TODO maybe add time of each
        self.data = []  # removing data that is now saved in file

    def start_scan_widget(self, tab):

        def press_start():
            if self.demo_mode.get():
                txt = "DEMO/OFFLINE"
            elif self.diagnostics_mode.get():
                txt = "DIAGNOSTICS"
            elif self.record_mode.get():
                txt = "RECORD SCAN"
            else:
                txt = '???'

            self.logger_box.module_logger.info(f"\n-------{txt}-------\nStart scan pressed")
            self.pb['value'] = 0
            self.root.update()  # testing
            # NOTE: HERE WE SHOULD START ANALYSIS?

            filename = f'{self.clue.get()}_' \
                   f'sineFreq({self.freq.get()})_' \
                   f'numFrames({self.nr_frames.get()})_' \
                   f'sineAmp({self.ampX.get()})_' \
                   f'stepAmp({self.ampY.get()})_' \
                   f'stepDim({self.dimY.get()})_' \
                   f'date({date.today().strftime("%y%m%d")})_' \
                   f'time({time.strftime("%Hh%Mm%Ss", time.localtime())})'
            self.data_file.set(filename)

            if not self.demo_mode.get():
                self.logger_box.module_logger.info(f"new file name => {filename}")
                t7.main_galvo_scan()  # try to perform scan (including prepp and connections)
                self.data_file.set(filename+'.timeres')

            # temp force plot for demo tuesday
            all_figs = self.ETA_analysis()
            plt_frame, canvas = self.pack_plot(self.plotting_frame, all_figs[0])  # FIXME: or maybe after plotting histo?
            plt_frame.grid(row=1, column=1, sticky="news", padx=0, pady=0)
            self.root.update()
            self.logger_box.module_logger.info("Done plotting")

        def press_close_stream():
            t7.close_stream = True

        def press_analyze():
            # TODO NOTE WORKING HERE PLOTTING ANALYSIS
            self.logger_box.module_logger.info("Pressed analyze")
            all_figs = self.ETA_analysis()
            plt_frame, canvas = self.pack_plot(self.plotting_frame, all_figs[0])  # FIXME: or maybe after plotting histo?
            plt_frame.grid(row=1, column=1, sticky="news", padx=0, pady=0)
            self.root.update()
            self.logger_box.module_logger.info("Done plotting")

        frm_send = tk.Frame(tab, relief=tk.RAISED, bd=2)

        tk.Label(frm_send, text=f' ').grid(row=1, column=0, sticky="ew")
        btn_start = tk.Button(frm_send, text="Start Scan", command=press_start, activeforeground='blue', highlightbackground=self.button_color)

        self.pb = ttk.Progressbar(frm_send, style='bar.Horizontal.TProgressbar', orient='horizontal', mode='determinate', length=100)  # progressbar

        btn_stop = tk.Button(frm_send, text="Analyze", command=press_analyze, activeforeground='blue', highlightbackground=self.button_color)
        btn_start.grid(row=0, column=0, sticky="nsew", padx=0, pady=1.5)
        #self.pb.grid(row=0, column=1, sticky="nsew")
        btn_stop.grid(row=0, column=2, sticky="nsew", padx=0, pady=1.5)

        tk.Button(frm_send, text="Close stream", command=press_close_stream, activeforeground='blue', highlightbackground=self.button_color).grid(row=0, column=3, sticky="nsew", padx=0, pady=1.5)

        return frm_send

    def plot_analysis_widget(self, tab):
        self.plotting_frame = tk.Frame(tab, relief=tk.RAISED, bd=2)

        return self.plotting_frame

    def log_scan_widget(self, tab):
        frm_log = tk.Frame(tab, relief=tk.RAISED, bd=2)

        tk.Label(frm_log, text=f'Log', font=('', 15)).grid(row=0, column=0, sticky="w")

        # TODO: MAKE LOG BOX A DIFFERENT COLOR AND ADD SCROLLBAR

        self.logger_box = Logger(frm_log)   # initialize log box from example. note: it grids itself in the class


        return frm_log

    @staticmethod
    def pack_plot(tab, fig, toolbar=True):

        # creating the Tkinter canvas containing the Matplotlib figure
        plt_frame = tk.Frame(tab, relief=tk.RAISED, bd=2)
        canvas = FigureCanvasTkAgg(fig, master=plt_frame)  # self.root)
        canvas.draw()

        # placing the canvas on the Tkinter window
        canvas.get_tk_widget().pack()

        if toolbar:
            # creating the Matplotlib toolbar
            toolbar = NavigationToolbar2Tk(canvas, plt_frame)  # self.root)
            toolbar.update()

            # placing the toolbar on the Tkinter window
            canvas.get_tk_widget().pack()

        return plt_frame, canvas

    def close(self, printlog):
        time.sleep(0.3)
        if printlog:
            gui.logger_box.module_logger.info("TODO: IMPLEMENT SOMETHING WHEN CLOSING")
        else:
            print("*** TODO: IMPLEMENT SOMETHING WHEN CLOSING")
        #self.sq.websq_disconnect()  # close SQWeb connection

    # TODO FIXME:
    # NOTE: try to change X, Y to Sine, Step. Check if it's correct!!
    def new_ETA_analysis(self):
        # ------IMPORTS-----
        import Swabian_Microscope_library as Q

        """# ------------ PARAMETERS AND CONSTANTS --------------
        eta_recipe = 'multiframe_recipe_bidirectional_segments_0.0.4.eta'  # 'microscope_bidirectional_segments_0.0.3.eta'

        # Parameters to locate timeres files:
        folder = "Data/230927/"     # Note: save location for data files
        clue = "digit_6"            # Note: (ex: 'higher_power', 'digit_8', 'digit6')
        timetag_file = None         # NOTE FIXME GET NAME OF CREATED FILE

        # Scan parameters:
        nr_frames = 10  # OBS: SET VALUE TO USE DATAFILE
        freq = 10  # OBS: SET VALUE TO USE DATAFILE
        ampX = 0.3  # --> step values between -0.3 and 0.3
        ampY = 0.3  # --> sine values between -0.3 and 0.3
        dimX = 100  # how many (stepwise) steps we take in scan
        bins = 20000  # how many bins/containers we get back for one period   #20000 is good --> 10k per row
        ch_sel = "h2" """

        # ------------ PARAMETERS AND CONSTANTS --------------
        eta_recipe = 'multiframe_recipe_bidirectional_segments_0.0.4.eta'  # 'microscope_bidirectional_segments_0.0.3.eta'

        # Parameters to locate timeres files:
        folder = "Data/230927/"     # Note: save location for data files
        self.clue = "digit_6"            # Note: (ex: 'higher_power', 'digit_8', 'digit6')
        timetag_file = None         # NOTE FIXME GET NAME OF CREATED FILE

        # Scan parameters:
        nr_frames = self.nr_frames.get()
        freq = self.freq.get()
        ampSine = self.ampX.get()    # sine  X
        ampStep = self.ampY.get()    # step  Y
        dimStep = self.dimY.get()    # how many steps/rows  Y
        bins = self.bins.get()
        ch_sel = self.ch_sel.get()
        clue = self.clue.get()

        # Playback Frame Rates for GIFs:
        # (time for one frame) = (number of steps)*(period) = (dimStep)/(frequency)

        dimSine = int(round(dimStep * (ampStep / ampSine)))  # How many pixels we want to use TODO: Get new data (where ampX != ampY) and test this relationship!

        scan_fps = freq / dimStep  # frame rate = (1/(time for one frame)) = (freq/dimStep)
        gif_rates = [1, 5, scan_fps]  # playback frame rates for each gif we want to create
        gif_notes = ["", "", "(live)"]  # notes for gif we want (for each playback frame rate)

        # ------------ MISC. RELATIONSHIPS ------------

        freq_ps = freq * 1e-12  # frequency scaled to unit picoseconds (ps)
        period_ps = 1 / freq_ps  # period in unit picoseconds (ps)
        binsize = int(round(period_ps / bins))  # how much time (in ps) each histogram bin is integrated over (=width of bins). Note that the current recipe returns "bins" values per period.

        gui.logger_box.module_logger.info(f"bins = {bins},  binsize = {binsize}")  # *{10e-12} picoseconds")
        gui.logger_box.module_logger.info(f"single frame scan time: {dimStep / freq} sec,  scan frame rate: {scan_fps} fps")
        gui.logger_box.module_logger.info(f"bins = {bins},  binsize = {binsize}")
        gui.logger_box.module_logger.info(f"single frame scan time: {dimStep / freq} sec,  scan frame rate: {scan_fps} fps")

        # NOTE: Below is a dictionary with all the parameters defined above. This way we can sent a dict with full access instead of individual arguments
        const = {
            "eta_recipe": eta_recipe,
            "timetag_file": timetag_file,
            "clue": clue,
            "folder": folder,
            "nr_frames": nr_frames,
            "freq": freq,
            "ampSine": ampSine,   # "ampX": ampX,
            "ampStep": ampStep,   # "ampY": ampY,
            "dimSine": dimSine,  # "dimX": dimX,
            "dimStep": dimStep,  # dimY
            "bins": bins,
            "ch_sel": ch_sel,
            "freq_ps": freq_ps,
            "period_ps": period_ps,
            "binsize": binsize,
            "scan_fps": scan_fps,
            "gif_rates": gif_rates,
            "gif_notes": gif_notes,
        }

        # --------- GET DATA AND HISTOGRAMS------------
        # quick version of "ad infinitum" code where we generate one image/frame at a time from ETA

        # --- GET TIMETAG FILE NAME, unless manually provided ---
        if timetag_file is None:
            gui.logger_box.module_logger.info("No timetag file provided")

        gui.logger_box.module_logger.info(f"Using datafile: {timetag_file}\n")
        gui.logger_box.module_logger.info(f"Using datafile: {timetag_file}\n")

        # --- PROVIDE WHICH MAIN FOLDER WE SAVE ANY ANALYSIS TO (ex. images, raw data files, etc.), DEPENDING ON WHICH ETA FILE
        st = timetag_file.find("date(")
        fin = timetag_file.find(".timeres")
        const["save_location"] = f"Analysis/({str(freq)}Hz)_{timetag_file[st:fin]}"  # This is the folder name for the folder where data, images, and anything else saved from analysis will be saved
        #       FOR EXAMPLE: const["save_location"] = Analysis/(100Hz)_date(230717)_time(14h02m31s)

        # --- EXTRACT AND ANALYZE DATA ---
        Q.eta_segmented_analysis_multiframe(const=const)   # TODO FIX FOR GUI


    # TODO:
    # - fix dimX dimY naming
    # - connect to actual data from GUI scan
    # - maybe move microscope analysis (library) code to this file

    def ETA_analysis(self):
        # ------IMPORTS-----
        import Swabian_Microscope_library as Q

        # ------------ PARAMETERS AND CONSTANTS --------------
        #eta_recipe = 'Swabian_multiframe_recipe_bidirectional_segments_0.0.4.eta'  # 'microscope_bidirectional_segments_0.0.3.eta'
        eta_recipe = gui.eta_recipe.get()  #'Swabian_multiframe_recipe_bidirectional_segments_marker4_20.eta'  # 'microscope_bidirectional_segments_0.0.3.eta'

        # Parameters to locate timeres files:
        folder = "Data/"  # Note: this is used to find the timeres file --> WRITE in your own data folder location
        clue = gui.clue.get()  # Note: this is used to help find the correct timeres file when only given frequency (ex: 'higher_power', 'digit_8', '13h44m23s')
        #       ^ex. for data in "230828": {"digit_6"}

        #timetag_file = 'nr_6_dup_marker_sineFreq(1)_numFrames(2)_sineAmp(0.3)_stepAmp(0.3)_stepDim(100)_date(231103)_time(14h48m42s).timeres'  # Note: let this be None if you want to use "clue" and "folder" to automatically find your file based on frequency
        #timetag_file = 'froggg_sineFreq(5.0)_numFrames(1)_sineAmp(0.3)_stepAmp(0.3)_stepDim(100)_date(240116)_time(09h53m12s).timeres'  # Note: let this be None if you want to use "clue" and "folder" to automatically find your file based on frequency
        #timetag_file = 'finalsaba.timeres'  # Note: let this be None if you want to use "clue" and "folder" to automatically find your file based on frequency
        #timetag_file = gui.data_file.get()
        timetag_file = 'sineFreq(1)_numFrames(2).timeres'  # temp for demo
        timetag_file = 'nr_6_dup_marker_sineFreq(10)_numFrames(2)_sineAmp(0.3)_stepAmp(0.3)_stepDim(100)_date(231103)_time(14h52m37s).timeres'
        #timetag_file = 'finalsaba_sineFreq(5.0)_numFrames(1).timeres'
        #timetag_file = 'froggg_sineFreq(5.0)_numFrames(1).timeres'
        #print("timetag file:", timetag_file)

        # Scan parameters:
        nr_frames = 2  # self.nr_frames.get()
        freq = 10  # self.freq.get()
        ampX = self.ampX.get()  # --> step values between -0.3 and 0.3
        ampY = self.ampY.get()  # --> sine values between -0.3 and 0.3
        dimX = self.dimY.get()  # how many (stepwise) steps we take in scan
        bins = self.bins.get()  # how many bins/containers we get back for one period   #20000 is good --> 10k per row
        ch_sel = 'h2'  # self.ch_sel.get()

        # Playback Frame Rates for GIFs:
        # (time for one frame) = (number of steps)*(period) = (dimX)/(frequency)
        scan_fps = freq / dimX  # frame rate = (1/(time for one frame)) = (freq/dimX)
        gif_rates = [1, 5, scan_fps]  # playback frame rates for each gif we want to create
        gif_notes = ["", "", "(live)"]  # notes for gif we want (for each playback frame rate)

        # ------------ MISC. RELATIONSHIPS ------------
        dimY = int(round(dimX * (ampY / ampX)))  # How many pixels we want to use TODO: Get new data (where ampX != ampY) and test this relationship!
        freq_ps = freq * 1e-12  # frequency scaled to unit picoseconds (ps)
        period_ps = 1 / freq_ps  # period in unit picoseconds (ps)
        binsize = int(round(
            period_ps / bins))  # how much time (in ps) each histogram bin is integrated over (=width of bins). Note that the current recipe returns "bins" values per period.

        self.logger_box.module_logger.info(f"bins = {bins},  binsize = {binsize}")  # *{10e-12} picoseconds")
        self.logger_box.module_logger.info(f"single frame scan time: {dimX / freq} sec,  scan frame rate: {scan_fps} fps")

        # NOTE: Below is a dictionary with all the parameters defined above. This way we can sent a dict with full access instead of individual arguments
        const = {
            "eta_recipe": eta_recipe,
            "timetag_file": timetag_file,
            "clue": clue,
            "folder": folder,
            "nr_frames": nr_frames,
            "freq": freq,
            "ampX": ampX,
            "ampY": ampY,
            "dimX": dimX,
            "bins": bins,
            "ch_sel": ch_sel,
            "dimY": dimY,
            "freq_ps": freq_ps,
            "period_ps": period_ps,
            "binsize": binsize,
            "scan_fps": scan_fps,
            "gif_rates": gif_rates,
            "gif_notes": gif_notes,
        }

        # --------- GET DATA AND HISTOGRAMS------------

        # quick version of "ad infinitum" code where we generate one image/frame at a time from ETA

        # --- GET TIMETAG FILE NAME, unless manually provided ---
        if timetag_file is None:
            timetag_file = Q.get_timres_name(folder, nr_frames, freq, clue=clue)
            const["timetag_file"] = timetag_file
        #self.logger_box.module_logger.info(f"Using datafile: {timetag_file}\n")

        # --- PROVIDE WHICH MAIN FOLDER WE SAVE ANY ANALYSIS TO (ex. images, raw data files, etc.), DEPENDING ON WHICH ETA FILE
        st = timetag_file.find("date(")
        fin = timetag_file.find(".timeres")
        const["save_location"] = f"Analysis/({str(freq)}Hz)_{timetag_file[st:fin]}"  # This is the folder name for the folder where data, images, and anything else saved from analysis will be saved
        #       FOR EXAMPLE: const["save_location"] = Analysis/(100Hz)_date(230717)_time(14h02m31s)

        # --- EXTRACT AND ANALYZE DATA ---
        # Q.eta_segmented_analysis_multiframe(const=const)   # note: all params we need are sent in with a dictionary. makes code cleaner

        # testing prev version
        all_figs = Q.bap_eta_segmented_analysis_multiframe(const=const)  # note: all params we need are sent in with a dictionary. makes code cleaner

        return all_figs


class Logger:   # example from: https://stackoverflow.com/questions/30266431/create-a-log-box-with-tkinter-text-widget

    # this item "module_logger" is visible only in this module,
    # (but you can create references to the same logger object from other modules
    # by calling getLogger with an argument equal to the name of this module)
    # this way, you can share or isolate loggers as desired across modules and across threads
    # ...so it is module-level logging and it takes the name of this module (by using __name__)
    # recommended per https://docs.python.org/2/library/logging.html

    def __init__(self, tk_window):

        self.module_logger = logging.getLogger(__name__)

        # create Tk object instance
        app = self.simpleapp_tk(tk_window)

        # setup logging handlers using the Tk instance created above the pattern below can be used in other threads...
        #   to allow other thread to send msgs to the gui
        # in this example, we set up two handlers just for demonstration (you could add a fileHandler, etc)
        stderrHandler = logging.StreamHandler()  # no arguments => stderr
        self.module_logger.addHandler(stderrHandler)
        guiHandler = self.MyHandlerText(app.mytext)
        self.module_logger.addHandler(guiHandler)
        self.module_logger.setLevel(logging.INFO)

        # NOTE THIS IS HOW YOU LOG INTO THE BOX:
        #self.module_logger.info("...some log text...")

    def simpleapp_tk(self, parent):
        #tk.Tk.__init__(self, parent)
        self.parent = parent

        #self.grid()

        self.mybutton = tk.Button(parent, text="Test")
        self.mybutton.grid(row=0, column=1, sticky='e')
        self.mybutton.bind("<ButtonRelease-1>", self.button_callback)

        """self.mybutton = tk.Button(parent, text="Clear")
        self.mybutton.grid(row=0, column=2, sticky='e')
        self.mybutton.bind("<ButtonRelease-1>", self.clear_button_callback)"""

        self.mytext = tk.Text(parent, state="disabled", height=15, width=40, wrap='word', background='#eeeeee')
        self.mytext.grid(row=1, column=0, columnspan=3)

        return self

    def button_callback(self, event):
        now = time.strftime("%H:%M:%S", time.localtime())
        msg = "...some msg"
        self.module_logger.info(f"({now})  ->  {msg}")

    class MyHandlerText(logging.StreamHandler):
        def __init__(self, textctrl):
            logging.StreamHandler.__init__(self)  # initialize parent
            self.textctrl = textctrl

        def emit(self, record):
            msg = self.format(record)
            self.textctrl.config(state="normal")
            self.textctrl.insert("end", msg + "\n")
            self.flush()
            self.textctrl.config(state="disabled")
            self.textctrl.see("end")
# TODO: ^ add clear button for logger


class T7:

    def __init__(self):
        self.handle = None  # Labjack device handle
        self.abort_scan = False  # Important safety bool for parameter checks
        self.close_stream = False
        # --------------- HARDCODED CLASS CONSTANTS BASED ON WIRING -------------

        self.wait_address = "WAIT_US_BLOCKING"
        self.x_address = "DAC1"  # Values sent from periodic buffer (which is not compatable with TDAC)
        self.y_address = "TDAC2"  # TickDAC via LJ port "FIO2" (TDAC IN PORTS FIO2 FIO3)

        # as of november 2023, changed wiring to FIO5 (with coaxial)
        self.q_M101_addr = "FIO5"
        self.q_M102_addr = "FIO5"

        # TRIGGERED STREAM, USING FIO0 and FIO1:
        self.tr_source_addr = "FIO0"  # Address for channel that outputs the trigger pulse
        self.tr_sink_addr = "DIO1"  # Address for channel that gets trigger pulse, and trigger stream on/off when pulse is recieved

        # Physical offset due to linearization of system (units: volts)
        self.x_offset = 0.505   # 0.59
        self.y_offset = -0.345  # -0.289

    # MAIN FUNCTION THAT PREPARES AND PERFORMS SCAN:
    def main_galvo_scan(self):
        gui.logger_box.module_logger.info("Getting scan parameters and generating scan sine and step values.")
        self.get_scan_parameters()
        self.get_step_values()
        self.get_sine_values()

        gui.logger_box.module_logger.info("Doing safety check on scan parameters.")
        SafetyTests().check_voltages()  # MOST IMPORTANT SO WE DON'T DAMAGE DEVICE WITH TOO HIGH VOLTAGE

        if not self.abort_scan:

            gui.logger_box.module_logger.info("Opening labjack connection")
            if not self.offline:
                self.open_labjack_connection()  # NOTE ONLINE ONLY
                # err = ljm.eStreamStop(t7.handle)   #

            gui.logger_box.module_logger.info("Populating command list")
            self.multi_populate_scan_cmd_list_burst()
            # self.multi_populate_scan_lists()  #### NEW NAME???

            # self.populate_buffer_stream()
            if not self.offline:
                self.fill_buffer_stream()  # NOTE ONLINE ONLY

            # Double check that scan command lists are safe
            gui.logger_box.module_logger.info("Checking for invalid addresses and values")
            SafetyTests().multi_check_cmd_list(self.aAddressesUp, self.aValuesUp, check_txt="Up Check")
            SafetyTests().multi_check_cmd_list(self.aAddressesDown, self.aValuesDown, check_txt="Down Check")

            if self.abort_scan:
                gui.logger_box.module_logger.info("Scan aborted")
                return

            gui.logger_box.module_logger.info("Configuring Stream Trigger")
            if self.useTrigger and not self.offline:  # alternative is that we use "STREAM_ENABLE" as a sort of trigger

                if self.close_stream:
                    err = ljm.eStreamStop(self.handle)   # TODO: HANDLE ERROR IF STREAM IS ALREADY ACTIVE!
                    self.close_stream = False

                self.configure_stream_trigger()  # NOTE ONLINE ONLY

            # Finish stream configs , replaces: ljm.eStreamStart(self.handle, self.b_scansPerRead,...)
            gui.logger_box.module_logger.info("Configuring Stream Start")
            if not self.offline:
                self.configure_stream_start()  # NOTE ONLINE ONLY

            gui.logger_box.module_logger.info("Creating socket connection with Qutag server.")
            if self.recordScan and not self.offline:
                #self.socket_connection()  # NOTE, TEMP FOR DEMO PURPOSES
                time.sleep(2)

            # AGAIN FINAL CHECK, MAYBE REMOVE LATER
            gui.logger_box.module_logger.info("Final safety check on values and addresses")
            SafetyTests().multi_check_cmd_list(self.aAddressesUp, self.aValuesUp, check_txt="Up Check")
            SafetyTests().multi_check_cmd_list(self.aAddressesDown, self.aValuesDown, check_txt="Down Check")
            SafetyTests().check_voltages()  # MOST IMPORTANT SO WE DON'T DAMAGE DEVICE WITH TOO HIGH VOLTAGE
            # ----
            # self.abort_scan = True  # temp  # NOTE
            if not self.abort_scan:
                self.multi_start_scan()  # NOTE ONLINE ONLY

    # Step 1) Sets all parameters depending on selected scan pattern and scan type
    def get_scan_parameters(self):
        # --------------- HARDCODED FOR THIS SIMPLER METHOD ------------------------------
        self.sine_addr = self.x_address
        self.sine_offset = self.x_offset
        self.step_addr = self.y_address
        self.step_offset = self.y_offset
        # --------------- Chosen scan parameters ----------------------------------------
        self.filename = gui.data_file.get()         #self.scanVariables.filename
        self.num_frames = gui.nr_frames.get()   # self.scanVariables.num_frames  # NOTE: NEW PARAM # how many frames/images we want to scan
        self.step_amp = gui.ampY.get()   # self.scanVariables.step_voltage  # voltage = angle*0.22
        self.step_dim = gui.dimY.get()   # self.scanVariables.step_dim

        self.recordScan = gui.record_mode.get()          # self.scanVariables.recordScan
        self.diagnostics = gui.diagnostics_mode.get()  # self.scanVariables.diagnostics
        self.offline = gui.demo_mode.get()             # self.scanVariables.offline

        self.q_pingQuTag = True  # self.scanVariables.pingQuTag   # default = True
        self.useTrigger = True  # self.scanVariables.useTrigger  # default = True
        self.ping101 = True  # self.scanVariables.ping101  # marker before step  # default = True --> marker AFTER  step, after sweep ends
        self.ping102 = True  # self.scanVariables.ping102  # marker after step   # default = True --> marker BEFORE step, before sweep starts

        #self.data_folder =... '/Users/juliawollter/Desktop/Microscope GUI/Data')  # TODO FIXME: unused gui parameter (for now)

        # -------

        # --------------- PLACEHOLDER VALUES --------------------------------------------
        # List of x and y values, and lists sent to Labjack:
        self.step_values = []  # values to step through
        self.step_values_up = []  # NOTE: NEW VARIABLE
        self.step_values_down = []  # NOTE: NEW VARIABLE

        self.step_times = []  # for plotting (single period)
        self.sine_values = []  # values for one sine period, for buffer
        self.sine_times = []  # for plotting (single period)
        # self.aAddresses = []
        # self.aValues = []
        self.aAddressesUp = []  # NOTE: NEW PARAM
        self.aValuesUp = []  # NOTE: NEW PARAM
        self.aAddressesDown = []  # NOTE: NEW PARAM
        self.aValuesDown = []  # NOTE: NEW PARAM
        # --------------- SINE ------------------------------
        self.b_max_buffer_size = 512  # Buffer stream size for y waveform values. --> Becomes resolution of sinewave period waveform == y_steps . i think it is max 512 samples (16-bit samples)?
        # Sine waveform:
        self.sine_amp = gui.ampX.get()      # self.scanVariables.sine_voltage
        self.sine_freq = gui.freq.get()    # self.scanVariables.sine_freq
        self.sine_period = 1 / self.sine_freq
        self.sine_phase = np.pi / 2
        self.sine_dim = int(
            self.b_max_buffer_size / 2)  # sine_dim = samplesToWrite = how many values we save to buffer stream = y_steps = resolution of one period of sinewave, --> sent to TickDAC --> sent to y servo input
        self.sine_delay = self.sine_period / self.sine_dim  # time between each y value in stream buffer     #self.sine_delay = 1 / (self.sine_dim / (2 * self.step_delay))
        # Buffer stream variables:
        self.b_scanRate = int(
            self.sine_dim / self.sine_period)  # scanrate = scans per second = samples per second for one address = (resolution for one sine period)/(one sine period)   NOTE: (2*self.step_delay) = self.sine_period (of sinewave)
        # TODO: what happens if we set "b_scansPerRead" to 0 instead?
        self.b_scansPerRead = self.b_scanRate  # int(self.b_scanRate / 2)  # NOTE: When performing stream OUT with no stream IN, ScansPerRead input parameter to LJM_eStreamStart is ignored. https://labjack.com/pages/support/?doc=%2Fsoftware-driver%2Fljm-users-guide%2Festreamstart
        self.b_targetAddress = ljm.nameToAddress(self.sine_addr)[0]
        self.b_streamOutIndex = 0  # index of: "STREAM_OUT0" I think this says which stream you want to get from (if you have several)
        self.b_aScanList = [ljm.nameToAddress("STREAM_OUT0")[0]]  # "STREAM_OUT0" == 4800
        self.b_nrAddresses = 1

        # -----------------------
        self.extra_delay = 0.001  # extra delay (seconds) to ensure that sine curve has reached a minimum
        self.step_delay = self.sine_period + self.extra_delay  # time between every X command. Should be half a period (i.e. time for one up sweep)

        # calculates constants we need to do wait_us_blocking for any frequency. NOTE!!! Can be moved to get_params func
        # Calculate residual delay for step delay (a full period)
        self.wait_delay = 0.1 * 1000000  # wait_delay = self.step_delay * 1000000   # "Delays for x microseconds. Range is 0-100000
        coveredDelay = 0.1 * int(self.step_delay / 0.1)
        self.remaining_delay = (round(self.step_delay / 0.1, 10) - int(self.step_delay / 0.1)) * 0.1 * 1000000

        # gui.logger_box.module_logger.info("total delay:", round(self.step_delay, 6))
        # gui.logger_box.module_logger.info("covered delay:", round(coveredDelay, 6), "seconds")
        # gui.logger_box.module_logger.info("remaining delay:", round(self.step_delay - coveredDelay, 6), "?=", self.remaining_delay/1000000)
        # -----------------------
        # Expected scan time:
        self.scanTime = (self.num_frames * 1.1 * self.step_dim * self.step_delay) + 5 + (
                    self.num_frames * 0.5)  # Expected time sent to qutag server    Note: it will be slightly higher than this which depends on how fast labjack can iterate between commands
        self.scanTime += 10  # FIXME

    # Step 2) Returns a list of step and sine values that the scan will perform
    def get_step_values(self):
        # populating "step_values" list with discrete values
        step_size = (2 * self.step_amp) / (self.step_dim - 1)  # step size of our x values
        k = -self.step_amp
        for i in range(self.step_dim):
            self.step_times.append(i * self.step_delay)  # for plotting
            self.step_values.append(round(k + self.step_offset, 10))
            k += step_size

    def get_sine_values(self):  # sine waveform
        # Change compared to before: now we don't ensure exactly symmetrical sine values for up/down sweeps.
        for i in range(self.sine_dim):
            t_curr = i * self.sine_delay
            val = self.sine_amp * np.sin((2 * np.pi * self.sine_freq * t_curr) - self.sine_phase)
            self.sine_times.append(t_curr)  # for plotting
            self.sine_values.append(round(val + self.sine_offset, 10))  # adding offset

    # Step 4) Connect to LabJack device
    def open_labjack_connection(self):
        self.handle = ljm.openS("T7", "ANY", "ANY")  # ErrorCheck(self.handle, "LJM_Open")
        info = ljm.getHandleInfo(self.handle)  # ErrorCheck(info, "PrintDeviceInfoFromHandle")
        # gui.logger_box.module_logger.info(f"Opened a LabJack with Device type: {info[0]}, Connection type: {info[1]},\n "
        # f"Serial number: {info[2]}, IP address: {ljm.numberToIP(info[3])}, Port: {info[4]},\n"
        # f"Max bytes per MB: {info[5]} \n")
        gui.logger_box.module_logger.info(f"Opened a LabJack with Device type: {info[0]}, Connection type: {info[1]},\n"
                                          f"Serial number: {info[2]}, IP address: {ljm.numberToIP(info[3])}, Port: {info[4]},\n"
                                          f"Max bytes per MB: {info[5]} \n")

    # Step 5) Connect to qu_tag
    def socket_connection(self, shutdown_server=False):
        """ Sets up a server ot communciate to the qutag computer to start a measurement
            Sends the file and scan time to the computer"""

        if gui.demo_mode.get():
            return   # in demo we don't want to create a server

        if shutdown_server:
            printlog = False  # will not log it but print instead
        else:
            printlog = True

        HEADERSIZE = 10
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Establishes a server
        # host = socket.gethostname()
        host = '130.237.35.177'  # IP address of this computer
        s.bind((host, 55555))
        s.listen(10)   # listen for 10 seconds???

        self.print_log(f'Setting up the server at: {host}', printlog)
        run_flag = True
        while run_flag:  # Keep looking for a connection
            clientsocket, address = s.accept()
            self.print_log(f'Connection from {address} has been established!', printlog)

            # Establish that a connection has been made and sends a greeting
            msg = 'welcome to the server!'
            msg = pickle.dumps(msg)
            msg = bytes(f'{len(msg):<{HEADERSIZE}}', 'utf-8') + msg
            r1 = clientsocket.send(msg)

            # Sends the relevant information
            # Mode is the qutag mode to produce a txt(0) or timeres file (1)
            if shutdown_server:
                mode = 7    # this indicates to the ssdp side that we are done
                self.print_log(f'Sending shutdown code!', printlog)
            elif self.diagnostics:
                mode = 0
            else:
                mode = 1

            msg = {'file': self.filename, 'scantime': self.scanTime, 'mode': mode}
            msg = pickle.dumps(msg)
            msg = bytes(f'{len(msg):<{HEADERSIZE}}', 'utf-8') + msg
            r2 = clientsocket.send(msg)
            if clientsocket:
                time.sleep(3)  # Give the qutag a few seconds to start up
                break

    # MULTI-DONE
    def multi_add_to_up_command_lists(self, addresses, values):
        # This is a precaution to prevent adding to one list without the other
        self.aAddressesUp += addresses
        self.aValuesUp += values

    # MULTI-DONE
    def multi_add_to_down_command_lists(self, addresses, values):
        # This is a precaution to prevent adding to one list without the other
        self.aAddressesDown += addresses
        self.aValuesDown += values

    # Step 6) Adds x values and qtag pings and other commands to command list
    # TODO: LOOK INTO TEST FUNCTIONS and what it was for
    # MULTI-DONE
    def multi_populate_scan_cmd_list_burst(self):  # USE TRIGGER WE HAVE SET UP PREVIOUSLY

        self.step_values_up = self.step_values.copy()  # NOTE: NEW ADDITIONS
        self.step_values_down = self.step_values.copy()  # NOTE: NEW ADDITIONS
        self.step_values_down.reverse()  # NOTE: NEW ADDITIONS

        self.cmd_pulse_trigger(state="arm")
        for step_idx in range(len(self.step_values)):
            self.cmd_marker(102)

            self.cmd_step_value(step_idx)

            self.cmd_marker(101)

            self.cmd_pulse_trigger(state="fire")

            self.multi_add_wait_delay()  # waits a period and a delta extra
            # ???? do below instead of multi_add_wait_delay to see that we do need to wait a full period
            # self.aAddresses += [self.wait_address]
            # self.aValues += [self.wait_delay]

            # RESETTING TRIGGER ETC:
            self.cmd_enable_trigger("off")
            self.cmd_pulse_trigger(state="arm")
            self.reset_num_scans()  # NEED TO RESET STUFF
            self.cmd_enable_trigger("on")

    # MULTI-DONE
    def test_multi_populate_scan_cmd_list_burst(self):  # USE TRIGGER WE HAVE SET UP PREVIOUSLY
        # gui.logger_box.module_logger.info("OPTION 1: external trigger")
        """
        _____________________________________________

        PREV METHOD:
        > trigger stream
        > for i in range(dimX):
            > marker 101 (maybe)
            > step
            > marker 102
            > wait --> t=period
        _____________________________________________

        NEW METHOD:
        arm trigger
        > repeat:
            > step
            > marker 101
            > fire trigger
            > wait --> t=period+delta
            > marker 102 (maybe)  ...  or this should be before we step?
            > reset trigger and stream configs for next round
        _____________________________________________
        """
        # do below instead of multi_add_wait_delay to see that we do need to wait a full period
        # self.aAddresses += [self.wait_address]
        # self.aValues += [self.wait_delay]

        self.step_values_up = self.step_values.copy()  # NOTE: NEW ADDITIONS
        self.step_values_down = self.step_values.copy()  # NOTE: NEW ADDITIONS
        self.step_values_down.reverse()  # NOTE: NEW ADDITIONS

        self.cmd_pulse_trigger(state="arm")
        for step_idx in range(len(self.step_values)):
            self.cmd_marker(102)
            self.cmd_step_value(step_idx)
            self.cmd_marker(101)

            self.cmd_pulse_trigger(state="fire")
            self.multi_add_wait_delay()  # waits a period and a delta extra
            # RESETTING TRIGGER ETC:
            self.cmd_enable_trigger("off")
            self.cmd_pulse_trigger(state="arm")
            self.reset_num_scans()  # NEED TO RESET STUFF
            self.cmd_enable_trigger("on")

            """
            self.cmd_pulse_trigger(state="fire")
            self.multi_add_wait_delay()  # waits a period and a delta extra
            # RESETTING TRIGGER ETC:
            self.cmd_enable_trigger("off")
            self.cmd_pulse_trigger(state="arm")
            self.reset_num_scans()  # NEED TO RESET STUFF
            self.cmd_enable_trigger("on")"""

    # MULTI-DONE
    def reset_num_scans(self):
        # self.aAddresses += ["STREAM_NUM_SCANS"]; self.aValues += [self.sine_dim]  # [int(self.sine_dim/2)]  # [self.sine_dim]
        self.multi_add_to_up_command_lists(addresses=["STREAM_NUM_SCANS"],
                                           values=[self.sine_dim])  # NOTE: NEW ADDITIONS
        self.multi_add_to_down_command_lists(addresses=["STREAM_NUM_SCANS"],
                                             values=[self.sine_dim])  # NOTE: NEW ADDITIONS

    # MULTI-DONE
    def multi_add_wait_delay(self):
        # Add as many 0.1s delays as we can fit
        for i in range(int(self.step_delay / 0.1)):
            # self.aAddresses += [self.wait_address] ; self.aValues += [self.wait_delay]
            self.multi_add_to_up_command_lists(addresses=[self.wait_address],
                                               values=[self.wait_delay])  # NOTE: NEW ADDITIONS
            self.multi_add_to_down_command_lists(addresses=[self.wait_address],
                                                 values=[self.wait_delay])  # NOTE: NEW ADDITIONS

        # Add any residual delay
        if self.remaining_delay > 0:
            # self.aAddresses += [self.wait_address] ; self.aValues += [self.remaining_delay]
            self.multi_add_to_up_command_lists(addresses=[self.wait_address],
                                               values=[self.remaining_delay])  # NOTE: NEW ADDITIONS
            self.multi_add_to_down_command_lists(addresses=[self.wait_address],
                                                 values=[self.remaining_delay])  # NOTE: NEW ADDITIONS

    # marker = {101, 102}
    # MULTI-DONE
    def cmd_marker(self, marker):
        # Add "step marker"
        if self.q_pingQuTag:
            if marker == 101 and self.ping101:
                # self.aAddresses += [self.q_M101_addr, self.q_M101_addr]; self.aValues += [1, 0]
                self.multi_add_to_up_command_lists(addresses=[self.q_M101_addr, self.wait_address, self.q_M101_addr],
                                                   values=[1, 1, 0])  # NOTE: NEW ADDITIONS
                self.multi_add_to_down_command_lists(addresses=[self.q_M101_addr, self.wait_address, self.q_M101_addr],
                                                     values=[1, 1, 0])  # NOTE: NEW ADDITIONS

            elif marker == 102 and self.ping102:  # note: not using end sweep address
                # self.aAddresses += [self.q_M102_addr, self.q_M102_addr]; self.aValues += [1, 0]
                self.multi_add_to_up_command_lists(addresses=[self.q_M102_addr, self.wait_address, self.q_M102_addr],
                                                   values=[1, 1, 0])  # NOTE: NEW ADDITIONS
                self.multi_add_to_down_command_lists(addresses=[self.q_M102_addr, self.wait_address, self.q_M102_addr],
                                                     values=[1, 1, 0])  # NOTE: NEW ADDITIONS
            else:
                pass

    # pulse state = {"arm", "fire"}
    # MULTI-DONE
    def cmd_pulse_trigger(self, state):
        if self.useTrigger:
            # Send a falling edge to the source of the trigger pulse, which is connected to the trigger channel --> Triggers stream.
            if state == "arm":
                # self.aAddresses += [self.tr_source_addr]; self.aValues += [1]     # arm/setup trigger --> 1=High
                self.multi_add_to_up_command_lists(addresses=[self.tr_source_addr], values=[1])  # NOTE: NEW ADDITIONS
                self.multi_add_to_down_command_lists(addresses=[self.tr_source_addr], values=[1])  # NOTE: NEW ADDITIONS
            elif state == "fire":  # trigger is set off by falling edge (edge from 1 to 0)
                # self.aAddresses += [self.tr_source_addr]; self.aValues += [0]     # execute trigger --> 0=Low
                self.multi_add_to_up_command_lists(addresses=[self.tr_source_addr], values=[0])  # NOTE: NEW ADDITIONS
                self.multi_add_to_down_command_lists(addresses=[self.tr_source_addr], values=[0])  # NOTE: NEW ADDITIONS
        else:
            gui.logger_box.module_logger.info("Error. Incorrect trigger based on 'useTrigger' parameter.")

    # enable state = {"on", "off"}
    # MULTI-DONE
    def cmd_enable_trigger(self, state):
        # instead of jumper trigger, use "ENABLE_STREAM"
        if self.useTrigger:  # if not self.useTrigger: before
            if state == "on":
                # self.aAddresses += ["STREAM_ENABLE"] ; self.aValues += [1]  # 1=High
                self.multi_add_to_up_command_lists(addresses=["STREAM_ENABLE"], values=[1])  # NOTE: NEW ADDITIONS
                self.multi_add_to_down_command_lists(addresses=["STREAM_ENABLE"], values=[1])  # NOTE: NEW ADDITIONS

            elif state == "off":
                # self.aAddresses += ["STREAM_ENABLE"] ; self.aValues += [0]  # 0=Low
                self.multi_add_to_up_command_lists(addresses=["STREAM_ENABLE"], values=[0])  # NOTE: NEW ADDITIONS
                self.multi_add_to_down_command_lists(addresses=["STREAM_ENABLE"], values=[0])  # NOTE: NEW ADDITIONS
            else:
                gui.logger_box.module_logger.info("Error in enable stream")
                self.abort_scan = True
        else:
            gui.logger_box.module_logger.info("Error. Incorrect enable trigger based on 'useTrigger' parameter.")

    # MULTI-DONE
    def cmd_step_value(self, idx):
        # Add step value
        # self.aAddresses += [self.step_addr] ; self.aValues += [step]
        self.multi_add_to_up_command_lists(addresses=[self.step_addr],
                                           values=[self.step_values_up[idx]])  # NOTE: NEW ADDITIONS
        self.multi_add_to_down_command_lists(addresses=[self.step_addr],
                                             values=[self.step_values_down[idx]])  # NOTE: NEW ADDITIONS

    # Step 7) Write sine waveform values to stream buffer (memory)
    def fill_buffer_stream(self):
        # https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/32-stream-mode-t-series-datasheet/#section-header-two-ttmre
        try:
            # gui.logger_box.module_logger.info("Initializing stream out... \n")
            err = ljm.periodicStreamOut(self.handle, self.b_streamOutIndex, self.b_targetAddress, self.b_scanRate,
                                        self.sine_dim, self.sine_values)
            # gui.logger_box.module_logger.info("Write to buffer error =", err)
        except ljm.LJMError:
            gui.logger_box.module_logger.info("Failed upload buffer vals")
            # ljm_stream_util.prepareForExit(self.handle)
            self.close_labjack_connection()
            raise

    def configure_stream_start(self):
        # previously --> ljm.eStreamStart(self.handle, self.b_scansPerRead, self.b_nrAddresses, self.b_aScanList, self.b_scanRate)
        try:
            # self.b_scansPerRead   TODO check
            # self.b_nrAddresses    done
            # self.b_aScanList      done
            # self.b_scanRate)      TODO check
            # NUM SCANS WORKS WITH PERIODIC SETUP
            # TODO: change back below
            ljm.eWriteName(self.handle, "STREAM_NUM_SCANS",
                           self.sine_dim)  # int(self.sine_dim/2))  # = 256, how many values in buffer we want to burst stream (full period of values)
            ljm.eWriteName(self.handle, "STREAM_SCANRATE_HZ", self.b_scanRate)  #
            ljm.eWriteName(self.handle, "STREAM_NUM_ADDRESSES",
                           self.b_nrAddresses)  # len(b_aScanList), nr of output channels/streams
            # ljm.eWriteName(self.handle, "STREAM_AUTO_TARGET", )  # TODO CHECK IF NEEDED
            ljm.eWriteName(self.handle, "STREAM_SCANLIST_ADDRESS0",
                           self.b_aScanList[0])  # TODO CHECK IF NEEDED AND WHAT IT IS
            # ljm.eWriteName(self.handle, "STREAM_DATATYPE", 0)  # ???? TODO CHECK IF NEEDED
            if self.useTrigger:
                ljm.eWriteName(self.handle, "STREAM_ENABLE", 1)  # ???? TODO CHECK IF NEEDED
            # TODO: READ BACK ACTUAL SCAN RATE
            # gui.logger_box.module_logger.info("Scan Rate:", self.b_scanRate, "vs.", scanRate)
        except ljm.LJMError:
            gui.logger_box.module_logger.info("Failed config buffer stream")
            self.close_labjack_connection()
            raise

    # Set up trigger for buffer stream:
    def configure_stream_trigger(self):
        # https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/132-dio-extended-features-t-series-datasheet/
        # gui.logger_box.module_logger.info("Configuring trigger")

        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX",
                       0)  # disabling triggered stream, also clears previous settings i think
        ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)  # Enabling internally-clocked stream.
        ljm.eWriteName(self.handle, "STREAM_RESOLUTION_INDEX", 0)
        ljm.eWriteName(self.handle, "STREAM_SETTLING_US", 0)
        ljm.eWriteName(self.handle, "AIN_ALL_RANGE", 0)
        ljm.eWriteName(self.handle, "AIN_ALL_NEGATIVE_CH", ljm.constants.GND)
        # ----
        # Configure LJM for unpredictable stream timing. By default, LJM will time out with an error while waiting for the stream trigger to occur.
        ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, ljm.constants.STREAM_SCANS_RETURN_ALL_OR_NONE)
        ljm.writeLibraryConfigS(ljm.constants.STREAM_RECEIVE_TIMEOUT_MS, 0)
        # ----
        # Define which address trigger is. Example:  2000 sets DIO0 / FIO0 as the stream trigger
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", ljm.nameToAddress(self.tr_sink_addr)[0])
        # ----
        # CONFIGS FOR TRIGGERED STREAM USING Extended Feature INDEX 12 "CONDITIONAL RESET":    (DIO2_EF_CONFIG_B,  DIO2_EF_CONFIG_C not needed)
        # Clear any previous settings on triggerName's Extended Feature registers. Must be value 0 during configuration
        ljm.eWriteName(self.handle, "%s_EF_ENABLE" % self.tr_sink_addr, 0)
        # Choose which extended feature to set
        ljm.eWriteName(self.handle, "%s_EF_INDEX" % self.tr_sink_addr, 12)
        # Set reset options, see bitmask options
        ljm.eWriteName(self.handle, "%s_EF_CONFIG_A" % self.tr_sink_addr,
                       0)  # 0: Falling edges , 1: Rising edges (<-i think, depends on bitmask)
        # Turn on the DIO-EF  --> Enable trigger once configs are done
        ljm.eWriteName(self.handle, "%s_EF_ENABLE" % self.tr_sink_addr, 1)

        # Arming/loading trigger. Trigger activates when self.tr_source_addr goes from 1 to 0 --> falling edge trigger
        # ljm.eWriteName(self.handle, self.tr_source_addr, 1)  --> moved to command list!

    # Step 8) Sets start scan positions of galvos
    def init_start_positions(self):
        if abs(self.step_values_up[0]) < 5 and abs(self.sine_values[0]) < 5:
            ljm.eWriteNames(self.handle, 2, [self.step_addr, self.sine_addr],
                            [self.step_values_up[0], self.sine_values[0]])
            # gui.logger_box.module_logger.info("Setting start positions for Step (up) and Sine values:", self.step_values_up[0], ", ", self.sine_values[0])
        else:
            self.abort_scan = True

    def test_trigger(self):
        if self.useTrigger:
            gui.logger_box.module_logger.info("")
            gui.logger_box.module_logger.info("-------")
            gui.logger_box.module_logger.info(f"Stream activated, but waiting. ")
            gui.logger_box.module_logger.info(f"You can trigger stream now via a falling edge on {self.tr_source_addr}.\n")
            gui.logger_box.module_logger.info("Sleeping 3 seconds to test trigger:")
            for i in range(1, 3):
                gui.logger_box.module_logger.info(i, "s ...")
                time.sleep(1)

    # Step 9) Actual scan is done here
    # MULTI-NEEDS CHECKING
    def multi_start_scan(self):
        # Start configured (but trigger-set) stream --> scan several frames
        try:

            if self.abort_scan or self.offline:  # last line of defense
                gui.logger_box.module_logger.info("Aborted scan (error or offline)")
                return

            gui.logger_box.module_logger.info("Initializing start position")
            self.init_start_positions()  # TODO later, consider moving galvo a bit at start up for best results
            time.sleep(4)  # FIXME give galvo a bit of time to reach start pos

            gui.logger_box.module_logger.info("Starting Scan")

            start_time = time.time()

            for i in range(self.num_frames):  # scan repeats for given number of frames
                #gui.pb['value'] += proc_step
                #gui.root.update()  # testing    # TODO NOTE FIXME, CHECK IF THIS AFFECTS ANYTHING TIME-WISE!!
                #gui.logger_box.module_logger.info(f"Frame", i, "done")

                if i % 2 == 0:  # if i is even
                    rc1 = ljm.eWriteNames(self.handle, len(self.aAddressesUp), self.aAddressesUp, self.aValuesUp)  # step left to right (or bottom to top)
                else:
                    rc2 = ljm.eWriteNames(self.handle, len(self.aAddressesDown), self.aAddressesDown, self.aValuesDown)  # step right to left (or top to bottom)

            end_time = time.time()

            err = ljm.eStreamStop(self.handle)
            time.sleep(1)
            gui.logger_box.module_logger.info("Stream closed")
            gui.logger_box.module_logger.info(f"Scan Done!"
                                              f"\n   ETA scan time = {int(self.scanTime)} seconds"
                                              f"\n   Theoretical scan time = {self.num_frames * self.step_dim * self.step_delay} seconds"
                                              f"\n   Actual scan time   = {round(end_time - start_time, 6)} seconds\n")

            # reset trigger and galvo positions to offset:
            rc = ljm.eWriteName(self.handle, self.tr_source_addr, 0)  # send 0 just in case to stop any input
            self.set_offset_pos()

        except ljm.LJMError:
            gui.logger_box.module_logger.info("Failed scan")
            err = ljm.eStreamStop(self.handle)
            self.close_labjack_connection()

            raise

    # Sets galvos to set offset positions
    def set_offset_pos(self):
        ljm.eWriteNames(self.handle, 2, [self.x_address, self.y_address], [self.x_offset, self.y_offset])

    def print_log(self, txt, printlog=True):
        if printlog:
            gui.logger_box.module_logger.info(txt)
        else:
            print("***", txt)

    # Terminates labjack connection
    def close_labjack_connection(self, printlog=True):

        self.print_log("Closing labjack connection...", printlog)
        if self.handle is None:
            self.print_log("T7 was not opened and therefore doesn't need closing", printlog)
        else:
            # reset galvo positions to offset:
            self.set_offset_pos()

            # stop stream in case it was active  # TODO: check if stopping a stream that is not active raises an error
            # err = ljm.eStreamStop(t7.handle)

            # clear trigger source voltage:
            ljm.eWriteName(self.handle, self.tr_source_addr, 0)  # send 0 just in case to stop any input

            # wait and close connection
            time.sleep(1)  # probably don't need, just in case there is still some data being transmitted
            err = ljm.close(self.handle)

            if err is None:
                self.print_log("Closing successful.", printlog)
            else:
                self.print_log(f"Problem closing T7 device. Error = {err}", printlog)


class SafetyTests:
    def check_voltages(self):
        # max is 5V but this gives a bit of margin, NOTE: val = 0.22*optical angle --> val = 1V is big enough for our scope
        max_voltage = 4

        # Checking that max allowed voltage is not changed. 5V is the absolute maximum allowed, but we give some margins
        if max_voltage > 4.5:
            gui.logger_box.module_logger.info("Error: to high max voltage, change back to 4V or consult script author")
            t7.abort_scan = True

        for step in t7.step_values:
            # CHECKING INPUT VALUES TO SERVO, MAX ALLOWED IS 5V, WE HAVE 4V FOR MARGINS
            if abs(step) > max_voltage:
                gui.logger_box.module_logger.info(f"Error: Too large voltage ({step}V) found in step list!")
                t7.abort_scan = True

        for val in t7.sine_values:
            # CHECKING INPUT VALUES TO SERVO, MAX ALLOWED IS 5V, WE HAVE 4V FOR MARGINS
            if abs(val) > max_voltage:
                gui.logger_box.module_logger.info(f"Error: Too large voltage ({val}V) found in sine list!")
                t7.abort_scan = True
            # CHECKING INPUT VALUES TO SENT VIA DAC, ONLY POSITIVE VALUES ALLOWED
            if val <= 0:
                gui.logger_box.module_logger.info(f"Error: Negative voltage ({val}V) found in list for DAC!")
                t7.abort_scan = True

    # MULTI-DONE
    def multi_check_cmd_list(self, addresses, values, check_txt=""):  # check_cmd_list(self):
        # gui.logger_box.module_logger.info(check_txt)

        # 1) WE CHECK THE COMMAND LIST LENGTHS
        if len(addresses) != len(values):
            gui.logger_box.module_logger.info("ERROR. NOT SAME COMMAND LIST LENGTHS. MISALIGNMENT DANGER.")
            t7.abort_scan = True

        # 2) WE CHECK THE STEPS  # TODO: maybe fix so we don't repeat this several times. although fix later
        for step in range(t7.step_dim):
            if t7.step_values[step] > 4:
                gui.logger_box.module_logger.info("ERROR. STEP VALUE TOO LARGE:", t7.step_values[step])
                t7.abort_scan = True
            if t7.step_values_up[step] > 4:
                gui.logger_box.module_logger.info("ERROR. STEP UP VALUE TOO LARGE:", t7.step_values_up[step])
                t7.abort_scan = True
            if t7.step_values_down[step] > 4:
                gui.logger_box.module_logger.info("ERROR. STEP DOWN VALUE TOO LARGE:", t7.step_values_down[step])
                t7.abort_scan = True

        if len(t7.step_values) != t7.step_dim:
            gui.logger_box.module_logger.info("ERROR. NOT ENOUGH STEP VALUES.", len(t7.step_values), "!=", t7.step_dim)
            t7.abort_scan = True
        if len(t7.step_values_up) != t7.step_dim:
            gui.logger_box.module_logger.info("ERROR. NOT ENOUGH STEP VALUES UP. ", len(t7.step_values_up), "!=", t7.step_dim)
            t7.abort_scan = True
        if len(t7.step_values_down) != t7.step_dim:
            gui.logger_box.module_logger.info("ERROR. NOT ENOUGH STEP VALUES DOWN.", len(t7.step_values_down), "!=", t7.step_dim)
            t7.abort_scan = True

        # 3) WE CHECK THE ADDRESSES IN
        for i in range(len(addresses)):
            if addresses[i] == t7.tr_source_addr:
                if values[i] != 0 and values[i] != 1:
                    gui.logger_box.module_logger.info("ERROR. INVALID VALUE FOR EDGE SOURCE VALUE")
                    t7.abort_scan = True

            elif addresses[i] == t7.tr_sink_addr:
                gui.logger_box.module_logger.info("ERROR. SINK SHOULD NOT BE A COMMAND TARGET ADDRESS")
                t7.abort_scan = True

            elif addresses[i] == t7.wait_address:
                if values[i] < 100 and values[i] != 0:
                    # gui.logger_box.module_logger.info("ERROR. ", values[i], " WAIT VALUE IS TOO SMALL.")
                    # t7.abort_scan = True
                    pass

            elif addresses[i] == t7.step_addr:
                if abs(values[i]) > 4:
                    gui.logger_box.module_logger.info("ERROR. VALUE TOO BIG")
                    t7.abort_scan = True

            elif addresses[i] == t7.sine_addr:
                gui.logger_box.module_logger.info("ERROR. SINE VALUE IN COMMAND LIST")
                t7.abort_scan = True
                if abs(values[i]) > 4:
                    gui.logger_box.module_logger.info("ERROR. VALUE TOO BIG")

            elif (addresses[i] == t7.q_M101_addr) or (addresses[i] == t7.q_M102_addr):
                if values[i] != 0 and values[i] != 1:
                    gui.logger_box.module_logger.info("ERROR. MARKER VALUE ERROR. MUST BE IN {0,1}")
                    t7.abort_scan = True

            elif addresses[i] == "STREAM_ENABLE" or addresses[i] == "STREAM_NUM_SCANS":
                pass
            else:
                gui.logger_box.module_logger.info(
                    f"'{addresses[i]}' ... Address not recognized or checked for in 'check_cmd_list()'. Aborting scan.")

                t7.abort_scan = True

        if t7.abort_scan:
            gui.logger_box.module_logger.info("Final Check Failed...\n")
        else:
            pass
            # gui.logger_box.module_logger.info("Final Check Succeeded!\n")


main()

"""
Write: 10 mA                --> x_i = 139.87160224013115
Read : 9.937685546874999 mA     x_i = b'\x00\x8b' == 139

Write: 20 mA                --> x_i = 279.7432044802623
Read : 19.946865234374997 mA    x_i = b'\x01\x17' == 279

Write: 40 mA                --> x_i = 559.4864089605246
Read : 39.965224609375 mA       x_i =  b'\x02/' == 559
"""

"""def plot_values():
    plt.figure()
    plt.plot(t7.sine_values)
    plt.plot(t7.sine_values, 'r.', label="sine values (in buffer)")
    plt.plot(t7.step_values)
    plt.plot(t7.step_values, 'g.',  label="step values OG")
    plt.legend()
    plt.xlabel("index")
    plt.ylabel("command voltage")

def plot_values_up():
    plt.figure()
    plt.plot(t7.sine_values)
    plt.plot(t7.sine_values, 'r.', label="sine values (in buffer)")
    plt.plot(t7.step_values_up)
    plt.plot(t7.step_values_up, 'g*',  label="step values UP")
    plt.legend()
    plt.xlabel("index")
    plt.ylabel("command voltage")

def plot_values_down():
    plt.figure()
    plt.plot(t7.sine_values)
    plt.plot(t7.sine_values, 'r.', label="sine values (in buffer)")
    plt.plot(t7.step_values_down)
    plt.plot(t7.step_values_down, 'g*',  label="step values DOWN")
    plt.legend()
    plt.xlabel("index")
    plt.ylabel("command voltage")"""



