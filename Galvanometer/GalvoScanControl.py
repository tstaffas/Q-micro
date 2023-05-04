import time
from datetime import date, datetime
from labjack import ljm
import struct
import socket
import pickle
import numpy as np
import matplotlib.pyplot as plt
import os
from turtle import *


"""
TODO:
- fix DLL problem with ljm library
- fix different time delays for x and y
- use "get_parameters()" depending on waveform and what params are needed
- finish writing buffer function
- can we start SSPD code from this file so we don't need to manually start both? 
- add more safety checks
- ask carol what frequency range is ok
- Ask Theo if he wants SSPD pings every time we step in x 
- create conversion table: FOV (um) to voltage input 
- use smoothed step function to prevent harsh jumps/steps (labjack signal gen)

"""

# UPDATED: 5/5-2023

class T7:

    def __init__(self, scantype, scanform, record, filename):
        """Note: All addresses are decided by SPI wiring"""

        # Opens communication with labjack and get's the handle back
        self.handle = ljm.openS("ANY", "ANY", "ANY")
        #ErrorCheck(self.handle, "LJM_Open");

        # Get and print handle information from the Labjack
        info = ljm.getHandleInfo(self.handle)
        #ErrorCheck(info, "PrintDeviceInfoFromHandle");

        print(f"Opened a LabJack with Device type: {info[0]}, Connection type: {info[1]},\n Serial number: {info[2]}, IP address: {ljm.numberToIP(info[3])}, Port: {info[4]},\nMax bytes per MB: {info[5]} \n" )

        # Create (scanning plan) list for addresses and values that is sent every column scanned
        self.aAddresses = []
        self.aValues = []

        # Create list for x values and y values (y: ONLY ONE COLUMN) we send as command to servo motor to set --> units: maybe voltage?
        self.x_values = []
        self.y_values = []   # list of all y values sent
        self.y_values_up = []
        self.y_values_down = []

        # Plotting lists (extras)
        self.t_values_up = []    # plotting
        self.t_values_down = []  # plotting

        # Servo and labjack addresses
        # TODO: DOUBLE CHECK THAT IT IS RIGHT TICK DAC ADDRESS
        self.x_address = "TDAC1"     # "30002"  "FIO1"
        self.y_address = "TDAC0"     # "30000"  "FIO0"
        self.wait_address = "WAIT_US_BLOCKING"

        # TODO: enter value
        self.wait_value = 10*1000           # t_delay = time_per_pixel =10*1000 #Integration time per pixel in micro seconds

        # Qtag addresses
        self.q_start_address = ""       # marks start of scan
        self.q_stop_address = ""        # marks end of scan
        self.q_step_address = ""        # marks each change in x value
        self.q_step_value = 0         # TODO: unsure if we need this

        # Define padding to include between every command sent

        # wait delay will be based on scan but with buffer we can do half (or maybe its actually a whole) period

        self.padding_addresses =  [  # TODO: we don't need padding anymore, only wait. --> change code - where this is called
            #self.q_start_address, self.wait_address,  self.q_start_address,
            self.wait_address,
            #self.q_stop_address,  self.wait_address,  self.q_stop_address
        ]

        self.padding_values = [
            #self.marker_voltage,   1,   0,
            self.wait_value,
            #self.marker_voltage,   1,   0
        ]

        # Misc
        self.scantype = scantype     # {"X", "Y", "XY"}
        self.scanform = scanform     # { "raster" , "lissajous",  "saw-sin" }
        self.record = record         # { True , False }
        self.filename = filename
        self.scantime = 10

        # Scan parameters

        # TODO: organize into cases waveform and create get Parameters function

        self.X_angle = 1           # mechanical angle in degrees i think
        self.Y_angle = 1           # mechanical angle in degrees i think
        self.x_static = 0
        self.y_static = 0
        self.x_steps = 100          # TODO: control and be variable
        self.y_steps = 10000        # TODO: hard code to max resolution we can have

        self.y_min = -self.Y_angle*0.22
        self.y_max = self.Y_angle*0.22
        self.x_min = -self.X_angle*0.22
        self.x_max = self.X_angle*0.22

        self.x_step_size = (self.x_max - self.x_min) / self.x_steps  # step size of our x values

        self.y_phase = np.pi/2
        self.t_half_period = 0
        self.t_step_size = 0

        self.x_frequency = 0  # lissalous tex so not now
        self.y_frequency = 0.5
        self.scan_iterations = 1
        self.y_sweep_iterations = 10

    def galvo_scan(self):
        # Step 1) Calculate all scan parameters
        self.get_scan_parameters()

        # Step 2) Check all input parameters (and abort if needed)
        foundError = self.auto_check_scan_parameters()
        if foundError:
            # Abort scan due to unacceptable values (if error is raised)
            return False

        # Step 3) Opens communication with qu-tag server
        if self.record:
            self.socket_connection()

        # Step 4)  Build list of commands and perform scan (depending on which scan is desired)
        foundError = self.decide_scan()
        if foundError:
            return False

        # Step 5) Fill buffer with sine values to loop over
        #self.create_buffer()

        # Step 6) Perform scan
        self.start_galvo_scan()


        return True

    # Step 1   TODO: move param definitions here
    def get_scan_parameters(self):

        # Y scan:
        # time step size for our y values (sine)t = [0, t_half_period]
        self.y_phase = np.pi/2
        self.t_half_period = 1 / ( 2* self.y_frequency)
        self.t_step_size = self.t_half_period / self.y_steps

    # Step 2
    # TODO: add more safety checks!
    def auto_check_scan_parameters(self):
        # Assuming no error --> raise_error = False. If raise_error becomes True, then we have encountered an error and will not scan
        raise_error = False

        # TODO: decide what good limits are
        max_val = 3  # max is 5V but this gives a bit of margin, NOTE: val = 0.22*optical angle --> val = 1V is big enough for our scope
        freq_max_x = 10000
        freq_min_x = 0.00001
        freq_max_y = 10000
        freq_min_y = 0.00001

        # Checking X- and Y static scan boundaries
        if (max_val < np.abs(self.x_static)) or (max_val < np.abs(self.y_static)) :
            print(f"Error: x_static = {self.x_static} or y_static = {self.y_static} is out of bounds!")
            raise_error = True

        # Checking X- and Y min/max input values
        if (max_val < np.abs(self.x_min)) or (max_val < np.abs(self.x_max)) or (max_val < np.abs(self.y_min)) or (max_val < np.abs(self.y_max)) :
            print(f"Error: [x_min, x_max] = [{self.x_min}, {self.x_max}] or [y_min, y_max] = [{self.y_min}, {self.y_max}] is out of bounds!")
            raise_error = True

        # Checking X- and Y frequencies
        if (self.x_frequency < freq_min_x) or (freq_max_x < self.x_frequency) or (self.y_frequency < freq_min_y) or (freq_max_y < self.y_frequency):
            print(f"Error: x_frequency = {self.x_frequency} or y_frequency = {self.y_frequency} is out of bounds!")
            raise_error = True

        """
        # Things that probably don't need to be checked:
        #   self.y_phase = 000
        #   self.t_half_period = 000
        #   self.x_step_size = (self.x_max - self.x_min) / self.x_steps
        
        if (self.scan_iterations < 0 or 10 < self.scan_iterations):
            print(f"Error: scan_iterations = {self.scan_iterations} is out of bounds!")   # unless we want to change it
            raise_error = True

        if (self.y_sweep_iterations < 0 or 100 < self.y_sweep_iterations):
            print(f"Error: y_sweep_iterations = {self.y_sweep_iterations} is out of bounds!")  # unless we want to change it
            raise_error = True

        if (self.x_steps < 1) or (500 < self.x_steps) or (self.y_steps < 10) or (500 < self.y_steps):
            print(f"Error: x_steps = {self.x_steps} or y_steps = {self.y_steps} is out of bounds!")  # unless we want to change it
            raise_error = True

        # Check if delta X is too small or large --> step size of our x values          # TODO: decide what min and max is for change in voltage input!!!
        d_x = np.Abs(self.x_max-self.x_min)/self.x_steps
        if (d_x < 0.001) or ( 0.1 < d_x) :
            print(f"Error: delta_x = {d_x} is out of bounds!")  # unless we want to change it
            raise_error = True
        """

        # Return false (no error) if we passed all the tests!
        return raise_error

    # Step 3
    def socket_connection(self):   # TODO: maybe make nicer later
        """ Sets up a server ot communciate to the qutag computer to start a measruement
            Sends the file and scan time to the computeer"""

        HEADERSIZE = 10

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Establishes a server
        host = socket.gethostname()
        host = '130.237.35.233'  # IP address of this computer
        s.bind((host, 55555))
        s.listen(10)

        print(f'Setting up the server at: {host}')
        run_flag = True
        while run_flag:  # Keep looking for a connection
            clientsocket, address = s.accept()
            print(f'Connection from {address} has been established!')

            # Establish that a connection has been made and sends a greeting
            msg = 'welcome to the server!'
            msg = pickle.dumps(msg)
            msg = bytes(f'{len(msg):<{HEADERSIZE}}', 'utf-8') + msg
            r1 = clientsocket.send(msg)

            # Sends the relevant information
            msg = {'file': self.filename, 'scantime': self.scantime}
            msg = pickle.dumps(msg)
            msg = bytes(f'{len(msg):<{HEADERSIZE}}', 'utf-8') + msg
            r2 = clientsocket.send(msg)
            if clientsocket:
                time.sleep(3)  # Give the qutag a few seconds to start up
                break

    # Step 5
    def decide_scan(self):
        if self.scantype == "X":
            self.scan_X()
        elif self.scantype == "Y":
            self.scan_Y()
        elif self.scantype == "XY":
            self.scan_XY()
        else:
            print("Invalid scan type selected! Please consult directions and try again.")
            return True
        return False   # returns false if no error is found

    # ---------- SCAN FUNCTIONS ----------
    def scan_X(self):

        # Step 0) Add time delay
        self.aAddresses.append(self.wait_address)
        self.aValues.append(self.wait_value)

        # Step 1) Add static y value that we want to scan at
        self.aAddresses.append(self.y_address)
        self.aValues.append(self.y_static)

        # Step 2)
        self.x_values = self.get_x_values()

        # Step 3)
        self.populate_lists(addr=self.x_address, list_values=self.x_values)

        # Step 4) Initiate start position of galvo at x_min
        rc = ljm.eWriteNames(self.handle, 1, [self.x_address], [self.x_min])

    def scan_Y(self):

        # Step 0) Add time delay
        self.aAddresses.append(self.wait_address)
        self.aValues.append(self.wait_value)

        # Step 1) Add static x value that we want to scan at:
        self.aAddresses.append(self.x_address)
        self.aValues.append(self.x_static)

        # Step 2) populating "y_values_up" list with discrete values of sine curve values
        self.y_values_up, self.y_values_down = self.get_y_values()

        # Step 3) now we have a list of sine values for HALF a period (one way) and a list for the other half period
        for i in range(self.y_sweep_iterations):
            if i % 2 == 0:  # sweep up
                self.populate_lists(self.y_address, self.y_values_up)
                self.y_values += self.y_values_up
            if i % 2 == 1:  # sweep down
                self.populate_lists(self.y_address, self.y_values_down)
                self.y_values += self.y_values_down


        # Step 4) Initiate start position of galvo at y_min
        rc = ljm.eWriteNames(self.handle, 1, [self.y_address], [self.y_min])

    def scan_XY(self):

        # Step 0) Add time delay
        self.aAddresses.append(self.wait_address)
        self.aValues.append(self.wait_value)

        # Step 1) Add static x value that we want to scan at:
        # --> skip since it is a 2D scan

        # Step 2) populating lists with discrete step values and values of sine curve values
        self.x_values = self.get_x_values()
        self.y_values_up, self.y_values_down = self.get_y_values()

        # Step 3) now we have a list of sine values for HALF a period (one way) and a list for the other half period
        for i in range(self.y_sweep_iterations):
            # Step one x value
            x_val = self.x_values[i]
            self.populate_lists(addr=self.x_address, list_values=[x_val])  # TODO: decide if we want to have the added time delay between x and y values as well...

            # Add all y values for one up/down sweep
            if i % 2 == 0:  # sweep up
                self.populate_lists(self.y_address, self.y_values_up)
                self.y_values += self.y_values_up
            if i % 2 == 1:  # sweep down
                self.populate_lists(self.y_address, self.y_values_down)
                self.y_values += self.y_values_down

        # Step 4) Initiate start position of galvo at y_min
        rc = ljm.eWriteNames(self.handle, 2, [self.x_address, self.y_address], [self.x_min, self.y_min])

    def get_x_values(self):
        # Create list for x values (ONLY ONE COLUMN) we send as command to servo motor to set --> units: maybe voltage?
        x_values = []

        # populating "x_values" list with discrete values
        k = self.x_min
        for i in range(self.x_steps):
            x_values.append(k)
            k += self.x_step_size

        return x_values

    def get_y_values(self):
        t_curr = 0
        y_values_up = []

        for i in range(self.y_steps):
            t_curr = i * self.t_step_size
            y_curr = self.y_max * np.sin((2 * np.pi * self.y_frequency * t_curr) - self.y_phase)

            self.t_values_up.append(t_curr)  # for plotting
            self.t_values_down.append(t_curr + self.t_half_period)  # for plotting
            y_values_up.append(y_curr)

        y_values_down = self.y_values_up.copy()
        y_values_down.reverse()
        return y_values_up, y_values_down

    def populate_lists(self, addr, list_values):
        for val in list_values:
            # maybe also add wait marker!
            #self.aAddresses.append(self.q_step_address)
            #self.aValues.append(self.q_step_value)

            # TODO: check if padding is done/added correctly
            self.aAddresses += self.padding_addresses
            self.aValues += self.padding_values

            self.aAddresses.append(addr)
            self.aValues.append(val)

    # TODO: finsih writing
    def prepare_buffer_stream(self):
        pass

        #Calling 'PeriodicStreamOut' will enable an out-stream that will
        #    loop over data values written to it when LJM_eStreamStart is called,
        #    then stop streaming values when LJM_eStreamStop is called.
        """
        # https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/32-stream-mode-t-series-datasheet/#section-header-two-ttmre
        STREAM_OUT0_ENABLE = 0                       # → Turn off just in case it was already on.
        STREAM_OUT0_TARGET = 1000                    # → Set the target to DAC0.
        STREAM_OUT0_BUFFER_ALLOCATE_NUM_BYTES = 512  # → A buffer to hold up to 256 values.
        STREAM_OUT0_ENABLE = 1                       # → Turn on Stream-Out0.

        STREAM_OUT0_BUFFER_F32 = [0.5, 1, 1.5, 1]       # → Write the four values one at a time or as an array.
        STREAM_OUT0_LOOP_NUM_VALUES = 4                 # → Loop four values.
        STREAM_OUT0_SET_LOOP = 1                        # → Begin using new data set immediately.

        # eWriteNameArray(self.handle, ...)


        # --------------------------------------------------------------
        #
        scanRate = 1000
        NUM_SCAN_ADDRESSES = 1
        scanList = ["STREAM_OUT0"]
        targetAddr = 1000  #// DAC0
        streamOutIndex = 0
        samplesToWrite = 512
        values = []
        # Open
        err = ljm.LJM_PeriodicStreamOut(
            self.handle,
            streamOutIndex, # The number assigned to this stream-out. See the Stream Out section of the T-series datasheet for more information.
            targetAddr,     # The target register to send stream-out data to. See the Stream Out section of the T-series datasheet for a list of potential targets.
            scanRate,       # The desired number of scans per second. Should be the same value as set in LJM_eStreamStart.
                            # Keep in mind that data rate limits are specified in Samples/Second which is equal to NumAddresses * Scans/Second or NumAddresses * ScanRate.
            samplesToWrite, # NumValues,      # The number of values to write to the stream-out buffer. This is also the number of values that will be looped over.
            values          # aWriteData      # The data array to be written to the stream-out buffer.
        )
        #ErrorCheck(err, "LJM_PeriodicStreamOut");

        scansPerRead = scanRate / 2
        aScanList = []
        aTypes = []

        err = ljm.LJM_eStreamStart( self.handle, scansPerRead, NUM_SCAN_ADDRESSES,  aScanList, & scanRate)
        #ErrorCheck(err, "LJM_eStreamStart");

        # Run for some time then stop the stream
        time.sleep(5)
        print("Stopping stream...\n")
        err = ljm.LJM_eStreamStop(self.handle)
        #ErrorCheck(err, "Problem closing stream");
        """

    def start_galvo_scan(self):

        start_time = time.time()

        # -------- SCAN STARTS ---------
        # send start marker to qtag  (maybe add time delay or other info to qtag)
        #rc = ljm.eWriteNames(self.handle, 3, [ self.q_start_address,  self.wait_address, self.q_start_address], [1,1,0])
        # check length of

        # sends scan commands to galvo/servo (and maybe step markers)
        rc = ljm.eWriteNames(self.handle, len(self.aAddresses), self.aAddresses, self.aValues)

        # sends stop commands to galvo/servo
        # TODO: maybe add stop buffer too
        rc = ljm.eWriteNames(self.handle, 2, [self.x_address, self.y_address], [0,0])

        # send end marker to qtag
       # rc = ljm.eWriteNames(self.handle, 3, [ self.q_stop_address,  self.wait_address, self.q_stop_address], [1,1,0])
        # -------- SCAN ENDS -----------

        end_time = time.time()
        print("Scan time:" , end_time-start_time)

    # TODO: finish writing this
    def sample_buffer(self):
        data = {'t': [], 'x_in': [], 'y_in': [], 'x_out': [], 'y_out': []}
        data['x_in'] = self.x_values
        data['y_in'] = self.y_values



        return data

    # Terminates labjack connection
    def close_labjack_connection(self):
        err = ljm.close(self.handle)
        # ErrorCheck(err, "Problem closing device");

    def draw_confimation(self):
        # plot to test
        plt.figure()
        plt.plot(self.t_values_up, self.y_values_up, 'r.')
        plt.plot(self.t_values_down, self.y_values_down, 'b.')
        plt.show()

        #ans = input("Looking at the figure, would you like to prodeed? (y/n)")


# __________ MANAGEMENT FUNCTIONS __________

def manage_local_files(filename, data):
    # OLD FILE NAME = f'{scan_name}_[{x_dim},{y_dim}]_[x,y]_{x_lim}_x_lim_{y_amp}_amp_{y_freq}_yfreq__bias_{bias}uA_{cts}kHz_Cts_{today}'  # where scan_name = '68_LV_0mA'

    # Get date and time
    curr_date = date.today().strftime("%y%m%d")     # required: from datetime import date
    curr_time = time.strftime("%Hh %Mm", time.localtime())

    # Create date folder
    if not os.path.exists(f'K:\\Microscope\\Data\\{curr_date}'):
        os.makedirs(f'K:\\Microscope\\Data\\{curr_date}')

    # Create measurement folder within date folder
    os.makedirs(f'K:\\Microscope\\Data\\{curr_date}\\Scan_{curr_time}')

    # Create file to save processed data
    file_output = open(f"K:\\Microscope\\Data\\{curr_date}\\Scan_{curr_time}\\{filename}.txt", "w")

    # Save data (x,y,t for now)
    save_data(data, file_output)

    # TODO: create and save figures
    # fig, name = plot_...()
    # save_mat_fig(fig, name, curr_date, curr_time)

def save_data(data, data_file):
    # Saving info about scan, which parameters, time taken, anything else we want to save for later review
    txt_in_file = ""                                # TODO: decide if and what text we want in our file
    data_file.write(f"{txt_in_file}\n")
    data_file.write(f"\n"
                    f"x_in, y_in are theoretical values that are sent to servos\n"
                    f"x_out, y_out are measured values that are sampled from servos\n")

    data_file.write('DATA:' + '\n' + '       t       |       x_in       |       y_in       |       x_out       |       y_out       ' + '\n')
    for j in range(len(data['t'])):
        str_row_j = str(data['t'][j]) + ' | ' + str(data['x_in'][j]) + ' | ' + str(data['y_in'][j]) + ' | ' + str(data['x_out'][j]) + ' | ' + str(data['y_out'][j]) + '\n'
        data_file.write(str_row_j)

    data_file.close()

def save_mat_fig(fig, name, curr_date, curr_time):
    file = open(f'K:\\Microscope\\Data\\{curr_date}\\Scan_{curr_time}\\{name}.mpl', 'wb')
    pickle.dump(fig, file)
    file.close()
    # https://stackoverflow.com/questions/67538039/python-equivalent-of-fig-file-from-matlab?noredirect=1&lq=1

def open_mat_fig(name, curr_date, curr_time):
    # ------- HOW TO OPEN PREVIOUS FIG FILE ------
    # fig_name = "fig_test_open"
    # open_mat_fig(fig_name)

    # https://stackoverflow.com/questions/67538039/python-equivalent-of-fig-file-from-matlab?noredirect=1&lq=1
    open_file = open(f'K:\\Microscope\\Data\\{curr_date}\\Scan_{curr_time}\\{name}.mpl', 'rb')
    open_figure = pickle.load(open_file)
    open_figure.show()


# TURTLE -----------------
# TODO: create draw method that takes the current parameters and draws a graph, then proceeds to ask the user to confirm if this is what they want.
#  If max or min is close enough to the FOV boundary, include the FOV box which is limited by the galvos

def turtle_figure(values):
    window = Screen()
    myPen = Turtle()
    config_turtle(window, myPen, values)

    for i in range(0, len(values)):
        x = values[i][1] * 2000
        y = (0.01 + values[i][2]) * 40000
        myPen.goto(x, y)
        myPen.pendown()
        # myPen.getscreen().update()   # not needed

    time.sleep(11)   # Needed since turtle window disappears otherwise ... i think

def config_turtle(window, myPen, values):

    window.bgcolor("#FFFFFF")
    myPen.hideturtle()
    # turtle.setworldcoordinates(-1, -1, 20, 20)
    #myPen.tracer(0)
    myPen.speed(0)
    myPen.pensize(3)
    myPen.color("#AA00AA")
    myPen.penup()
    myPen.goto(1, 110)

    minx = 1000000;  maxx = -1000000;  miny = 1000000;  maxy = -1000000
    for i in range(0, len(values)):
     x = values[i][1] * 2000
     y = (0.01 + values[i][2]) * 40000
     if x < minx:
      minx = x
     if x > maxx:
      maxx = x
     if y < miny:
      miny = y
     if y > maxy:
      maxy = y

    print(minx, maxx, miny, maxy)
    #window.setworldcoordinates(minx, miny, maxx, maxy)
# ------------------------


if __name__ == '__main__':

    scantype = "X"          ### { "X" , "Y" , "XY" }
    scanform = "raster"     ### { "raster" , "lissajous",  "saw-sin" }
    record = False
    filename = "placeholderFilename"

    # 1) Initiates class and connects to labjack
    t7 = T7(scantype, scanform, record, filename)

    # 2) Perpare scan
    noError = t7.galvo_scan()

    if noError:
        pass

        # 3) Stream values from buffer
        #data = t7.sample_buffer()

        # 4) Save data, plot figures, etc.
        #manage_local_files(filename, data)

    # 5) Terminates labjack connection
    t7.close_labjack_connection()


