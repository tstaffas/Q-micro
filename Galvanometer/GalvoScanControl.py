import time
from datetime import date, datetime
from labjack import ljm   # I think this requires that we have the labjack folder in our dir for access
import struct
import socket
import pickle
import numpy as np
import matplotlib.pyplot as plt
import os
import turtle as ttl

# Note: in case of problems with labjack library dll
#   --> is located in C:\Program Files (x86)\LabJack\Drivers

# UPDATED: 17/5-2023

class ErrorChecks:

    def __init__(self, max_voltage, max_x_steps, min_y_freq, max_y_freq, max_sample_rate):
        # self.abort_scan = False
        self.max_voltage = max_voltage
        self.max_x_steps = max_x_steps
        self.min_y_freq = min_y_freq
        self.max_y_freq = max_y_freq
        self.max_sample_rate = max_sample_rate

    def check_voltages(self):
        # Checking that max allowed voltage is not changed. 5V is the absolute maximum allowed, but we give some margins
        if self.max_voltage > 5:
            t7.abort_scan = True

        # CHECKING INPUT VALUES TO SERVOS
        for x_val in t7.x_values:
            if abs(x_val) > self.max_voltage:
                print(f"Error: Too large voltage ({x_val}V) found in X list!")
                # self.abort_scan = True
                t7.abort_scan = True
        for y_val in t7.y_values:
            if abs(y_val) > self.max_voltage:
                print(f"Error: Too large voltage ({y_val}V) found in Y list!")
                # self.abort_scan = True
                t7.abort_scan = True

    def check_scan_type(self):
        # CHECKING SCAN TYPES
        if t7.scanType not in ["X", "Y", "XY"]:
            print("Error: Invalid scan type provided!")
            # self.abort_scan = True
            t7.abort_scan = True

    def check_x_static(self):
        # STATIC SCAN STATIC X
        if self.max_voltage < np.abs(t7.x_static):
            print(f"Error: x_static = {t7.x_static} is out of bounds!")
            # self.abort_scan = True
            t7.abort_scan = True

    def check_y_static(self):
        # STATIC SCAN STATIC Y
        if self.max_voltage < np.abs(t7.y_static):
            print(f"Error: y_static = {t7.y_static} is out of bounds!")
            # self.abort_scan = True
            t7.abort_scan = True

    def check_boundaries(self):
        # CHECKING MIN/MAX VALUES (boundaries)
        if (self.max_voltage < np.abs(t7.x_min)) or (self.max_voltage < np.abs(t7.x_max)) or (self.max_voltage < np.abs(t7.y_min)) or (self.max_voltage < np.abs(t7.y_max)):
            print(f"Error: [x_min, x_max] = [{t7.x_min}, {t7.x_max}] or [y_min, y_max] = [{t7.y_min}, {t7.y_max}] is out of bounds!")
            # self.abort_scan = True
            t7.abort_scan = True

    def check_y_frequency(self):
        # CHECKING Y FREQUENCY
        if (t7.y_frequency < self.min_y_freq) or (self.max_y_freq < t7.y_frequency):
            print(f"Error: y_frequency = {t7.y_frequency} is out of bounds!")
            # self.abort_scan = True
            t7.abort_scan = True

    def check_x_steps(self):
        # CHECKING NUMBER OF X STEPS BASED ON REPEATABILITY (= 10 [µrad] ≈ 0.0006 [degrees]) https://www.thorlabs.de/thorproduct.cfm?partnumber=QS7XY-AG
        if (t7.x_steps < 1) or (t7.x_steps > self.max_x_steps):
            print(f"Error: Too many steps to do in x! (based on repeatability specs)")
            # self.abort_scan = True
            t7.abort_scan = True

    def check_samplerate(self):
        # CHECKING SAMPLE RATE BASED ON:  maxSampleRate = 100000 / numChannels   as we likely have under 10 channels (~6-7)
        samplerate = 0          # TODO: calculate!!!
        if self.max_sample_rate < samplerate:
            print(f"Error: Too high sample rate for labjack (given other params)!")
            # self.abort_scan = True
            t7.abort_scan = True


class T7:
    # --------------- HARDCODED CLASS CONSTANT (for all scan types) -------------
    # Servo and labjack addresses, note: we are using tickDAC
    x_address = "TDAC1"         # "30002"  "FIO1"
    y_address = "TDAC0"         # "30000"  "FIO0"
    wait_address = "WAIT_US_BLOCKING"
    # Qutag addresses
    q_start_address = ""        # marks start of scan               # TODO: FILL IN
    q_stop_address = ""         # marks end of scan                 # TODO: FILL IN
    q_step_address = ""         # marks each change in x value      # TODO: FILL IN
    q_step_value = 0            # unsure if we need this            # TODO: FILL IN
    # Periodic waveform buffer for outputing Y voltage
    b_aScanList = [4800]        # "STREAM_OUT0"
    b_nrAddresses = 1           # only one buffer we use
    b_targetAddress = 30000     # TDAC0 = fast axis = y axis
    b_streamOutIndex = 0        # index of: "STREAM_OUT0" I think this says which stream you want to get from (if you have several)
    max_buffer_size = 256       # Buffer stream size for y waveform values. --> Becomes resolution of sinewave period waveform    # TODO: FILL IN, check how many y_values we can fit in a buffer, max 512 (16-bit samples)

    def __init__(self, param, scanForm, record, pingQTag):
        # --------------- ATTRIBUTES ----------------------
        self.q_pingQTag = pingQTag      # bool for whether we want to ping the qtag with the scan
        self.record = record            # { True , False }
        self.typeObj = param             # class for {"X", "Y", "XY"}
        self.scanForm = scanForm        # { "raster" , "lissajous",  "saw-sin" }   # not used at the moment
        self.scanType = param.scan_type   # {"X", "Y", "XY"}
        self.filename = param.filename

        # parameters required by all types of scans. Missing parameters are declared and defined in "get_scan_parameters()"
        self.x_angle = param.x_angle
        self.y_angle = param.y_angle
        self.x_steps = param.x_steps
        # --------------- PLACEHOLDER VALUES -------------------------------------------------------
        self.handle = None               # Labjack device handle
        self.abort_scan = False         # Safety bool for parameter check
        self.aAddresses = []            # Scanning plan: list of addresses for all the commands
        self.aValues = []               # Scanning plan: list of values for all the commands
        self.x_values = []              # List for x values that are are set during scan
        self.y_values = []              # List for y values that are are set during scan

        # PLOTTING:
        self.plt_up_y = []
        self.plt_down_y = []
        self.single_x_times = []
        self.single_y_times = []

    # MAIN FUNCTION THAT PREPARES AND PERFORMS SCAN
    def main_galvo_scan(self):
        # Step 1) Calculate all scan parameters
        print("Step 1) Defining scan parameters.")
        self.get_scan_parameters()

        # Step 2) Get a list of x and y values given scan parameters
        print("Step 2) Generating scan x,y values.")
        self.x_values = self.get_x_values()
        self.y_values = self.get_y_values()

        # Step 3) Check all input parameters (and abort if needed)
        print("Step 3) Doing safety check on scan parameters.")
        self.auto_check_scan_parameters()

        # TEMP, maybe remove later:
        Plotting().plot_theoretical()

        # Step 3.5) Check to abort  (due to error in "self.auto_check_scan_parameters()")
        print("Step 3.5) Check if we need to abort scan.")
        if self.abort_scan:
            print("Aborting scan.")
            # Abort scan due to unacceptable values (if error is raised)
            return False
        else:
            print("Error check succeeded. (but failed force quit test)")

        return False

        print("Step 4) Opening labjack connection")
        # Step 4) Open communication with labjack handle
        #self.open_labjack_connection()

        # Step 5) Opens communication with qu-tag server
        if self.record:
            print("Creating socket connection with Qutag server.")
            self.socket_connection()

        # Step 6) Populates command list with calculated x values and addresses
        print("Step 6) Populating command list.")
        self.populate_lists(addr=self.x_address, list_values=self.x_values, t_delay=self.x_delay)

        # Step 7) Fill buffer with sine values to loop over - Configure labjack buffer
        print("Step 7) Filling LJ stream buffer with Y values.")
        #self.prepare_buffer_stream()

        # Step 8) Initiate start position of galvos
        print("Step 8) (not) Setting start positions of galvos.")
        #self.init_start_positions()
        time.sleep(1)  # wait 1 second to give galvos time to get to start positions

        # Step 9) Perform scan
        print("Step 9) (not) Performing scan...")
        #self.start_scan()

        return True

    # Step 1) Sets all parameters depending on selected scanform and scantype
    def get_scan_parameters(self):

        self.x_min = -self.x_angle * 0.22
        self.x_max = self.x_angle * 0.22
        self.y_min = -self.y_angle * 0.22
        self.y_max = self.y_angle * 0.22

        # X is variable, Y is static
        if self.scanType == "X":
            # VARIABLES:
            self.y_static = self.typeObj.y_static
            # HARDCODED:
            self.x_delay = 10 / self.x_steps  # hardcoded to a 10 seconds scan:  x_delay [s/step]= 10 [s] / x_steps [step]
            self.y_waveform = 'static'
            self.b_samplesToWrite = self.max_buffer_size
            self.y_steps = self.b_samplesToWrite
            # UNUSED:   self.x_static = self.y_frequency = self.y_period = None

        # X is static, Y is variable
        elif self.scanType == "Y":
            # VARIABLES:
            self.y_frequency = self.typeObj.y_frequency  # given is Hz
            self.x_static = self.typeObj.x_static
            # HARDCODED:
            self.y_waveform = 'sine'
            # UNUSED:  self.y_static = None

        # X is variable, Y is variable
        elif self.scanType == "XY":
            # VARIABLES:
            self.y_frequency = self.typeObj.y_frequency          # given is Hz
            # HARDCODED:
            self.y_waveform = 'sine'
            # UNUSED:   self.x_static = self.y_static = None

        if self.y_waveform == 'sine':  # for --> self.scanType == "Y" or "XY"
            # HARDCODED:
            self.b_samplesToWrite = self.max_buffer_size   # how many values we save to buffer
            self.y_steps = int(self.b_samplesToWrite / 2)  # NOTE: y_steps is for one sweep, which is only half a period but we want to save values for a whole period
            self.y_phase = np.pi / 2
            self.y_period = 1 / self.y_frequency
            self.x_delay = self.y_period / 2  # time between every X command. Should be half a period (i.e. time for one up sweep)

        self.b_scanRate = self.b_samplesToWrite / (2*self.x_delay)  # NOTE: (2*self.x_delay) = self.y_period (of sinewave) # = scans per second = samples per second for one address
        self.b_scansPerRead = self.b_scanRate / 2  # When performing stream out with no stream in, ScansPerRead input parameter to LJM_eStreamStartis ignored. https://labjack.com/pages/support/?doc=%2Fsoftware-driver%2Fljm-users-guide%2Festreamstart
        self.y_delay = 1 / self.b_scanRate  # time between each y value in stream buffer
        self.scanTime = self.x_steps * self.x_delay  # Note: it will be slightly higher than this which depends on how fast labjack can iterate between commands
        print(f"Expected scan time = {self.scanTime}")

    # Step 2) Returns a list of x values that the scan will perform
    def get_x_values(self):
        # Create list for x values (ONLY ONE COLUMN) we send as command to servo motor to set --> units: maybe voltage?
        x_values = []

        # If we want to step x values
        if self.scanType == 'X' or self.scanType == 'XY':
            # populating "x_values" list with discrete values
            x_step_size = (self.x_max - self.x_min) / self.x_steps  # step size of our x values
            k = self.x_min
            #x_values.append(k)
            for i in range(self.x_steps):
                x_values.append(k)
                self.single_x_times.append(i * self.x_delay)  # for plotting
                k += x_step_size


            return x_values

        elif self.scanType == 'Y':
            # populating "x_values" list with x_Static a number of times ( == self.x_steps)
            for i in range(self.x_steps):
                x_values.append(self.x_static)
                self.single_x_times.append(i * self.x_delay)  # for plotting
            return x_values

        else:
            print("Error in get x values! Invalid scan type given.")
            self.abort_scan = True
            return x_values

    # Step 2) Returns a list of y values that the scan will perform
    def get_y_values(self):
        # if we are only changing x then the buffer only needs one value --> Y STATIC
        if self.scanType == 'X':
            # in this case: self.y_waveform == 'constant'
            y_vals = []
            for i in range(self.b_samplesToWrite):
                y_vals.append(self.y_static)
                self.single_y_times.append(i*self.y_delay)  # for plotting
            return y_vals

        elif self.scanType == 'Y' or self.scanType == 'XY':
            # if Y has periodic waveform:
            y_values_up = []
            t_curr = 0
            t_step_size = self.y_period / self.b_samplesToWrite
            n_half_period = int(self.b_samplesToWrite/2)  # NOTE: self.y_steps == n_half_period

            single_y_times_up = []  # for plotting
            single_y_times_down = []  # for plotting

            if self.y_waveform == 'sine':
                for i in range(n_half_period):
                    #t_curr += t_step_size
                    t_curr = i*self.y_delay

                    single_y_times_up.append(t_curr)  # for plotting
                    single_y_times_down.append(t_curr + (self.y_period / 2))  # for plotting
                    #print(i*self.y_delay, "=?", t_curr)

                    y_curr = self.y_max * np.sin((2 * np.pi * self.y_frequency * t_curr) - self.y_phase)
                    y_values_up.append(y_curr)

            elif self.y_waveform == 'saw':  # WARNING: Do not use this yet!!!
                y_curr = self.y_min
                n_half_period = int(self.b_samplesToWrite / 2)
                dy = (self.y_max - self.y_min) / self.y_steps   # NOTE: self.y_steps == n_half_period

                for i in range(n_half_period):
                    t_curr += t_step_size
                    single_y_times_up.append(t_curr)  # for plotting
                    single_y_times_down.append(t_curr + (self.y_period/2))  # for plotting

                    y_curr += dy  # linear function from y_min to y_max
                    y_values_up.append(y_curr)

            elif self.y_waveform == 'custom1':  # WARNING: Do not use this yet!!!
                print("Custom waveforms are not implemented yet. Setting Y to static with value 0")
                return [0]
            else:
                print("Error defining waveform for Y")
                self.abort_scan = True
                return []

            y_values_down = y_values_up.copy()
            y_values_down.reverse()
            print(y_values_up)
            print(y_values_down)
            y_values = y_values_up + y_values_down  # merge two lists into new list --> this is one period that we will repeat with buffer

            self.single_y_times =  single_y_times_up + single_y_times_down   # FOR PLOTTING
            self.plt_up_y = y_values_up      # FOR PLOTTING
            self.plt_down_y = y_values_down  # FOR PLOTTING

            return y_values

        else:
            print("Error in get_y_values! Invalid scan type given.")
            self.abort_scan = True
            return []

    # Step 3) Error checks
    def auto_check_scan_parameters(self):
        # TODO: add check for buffer length and ensure there is enough space to write all self.y_values

        # HARDCODED LIMITS WE TEST AGAINST
        max_x_steps = (self.x_angle) / 0.0006  # if self.x_angle is optical
        max_sample_rate = 10000  # maxSampleRate = 100000 / numChannels   and we likely have under 10 channels (~6-7)
        max_voltage = 4  # max is 5V but this gives a bit of margin, NOTE: val = 0.22*optical angle --> val = 1V is big enough for our scope
        max_y_freq = 10000  # TODO: calculate a max frequency
        min_y_freq = 0.00001  # TODO: calculate a min frequency

        # initiate error check class
        err = ErrorChecks(max_voltage, max_x_steps, min_y_freq, max_y_freq, max_sample_rate)

        # MOST IMPORTANT SO WE DON'T DAMAGE DEVICE
        err.check_voltages()  # CHECKING INPUT VALUES TO SERVOS
        err.check_boundaries()  # CHECKING MIN/MAX VALUES

        # USEFUL CHECKS TO ENSURE THAT SCAN IS SUCCESSFUL
        err.check_scan_type()  # CHECKING SCAN TYPES
        err.check_x_steps()  # CHECKING NUMBER OF X STEPS BASED ON REPEATABILITY
        err.check_samplerate()  # CHECKING MAX SAMPLE RATE

        # BELOW: ADDITIONAL SCANS THAT ARE "SCANTYPE" SPECIFIC
        if self.scanType == "X":
            # variables not used and not yet checked:  self.y_period, self.y_steps
            err.check_y_static()  # CHECKING SCAN STATIC Y

        if self.scanType == "Y":
            err.check_x_static()  # CHECKING SCAN STATIC X
            err.check_y_frequency()  # CHECKING Y FREQUENCY

        if self.scanType == "XY":
            err.check_y_frequency()  # CHECKING Y FREQUENCY

    # Step 4) Connect to labjack device
    def open_labjack_connection(self):
        self.handle = ljm.openS("T7", "ANY", "ANY")  # ErrorCheck(self.handle, "LJM_Open")
        info = ljm.getHandleInfo(self.handle)  # ErrorCheck(info, "PrintDeviceInfoFromHandle")
        print(f"Opened a LabJack with Device type: {info[0]}, Connection type: {info[1]},\n Serial number: {info[2]}, IP address: {ljm.numberToIP(info[3])}, Port: {info[4]},\nMax bytes per MB: {info[5]} \n")

    # Step 5) Connect to qu_tag
    def socket_connection(self):
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
            msg = {'file': self.filename, 'scantime': self.scanTime}
            msg = pickle.dumps(msg)
            msg = bytes(f'{len(msg):<{HEADERSIZE}}', 'utf-8') + msg
            r2 = clientsocket.send(msg)
            if clientsocket:
                time.sleep(3)  # Give the qutag a few seconds to start up
                break

    # Step 6) Adds x values and qtag pings and other commands to command list
    def populate_lists(self, addr, list_values, t_delay):

        if self.q_pingQTag:
            # Send start marker to qtag (maybe add time delay or other info to qtag)
            self.aAddresses += [self.q_start_address, self.wait_address, self.q_start_address]
            self.aValues += [1, self.x_delay, 0]

        # Add x values to command list
        for val in list_values:
            # Add delay (can be different delays for different lists) and one value at a time to list
            self.aAddresses += [addr, self.wait_address]
            self.aValues += [val, t_delay]

        if self.q_pingQTag:
            # Send end marker to qtag (maybe add time delay or other info to qtag)
            self.aAddresses += [self.q_stop_address, self.wait_address, self.q_stop_address]
            self.aValues += [1, self.x_delay, 0]

    # Step 7) Write y waveform values to stream buffer (memory)
    def prepare_buffer_stream(self):
        # https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/32-stream-mode-t-series-datasheet/#section-header-two-ttmre
        err = ljm.periodicStreamOut(self.handle, self.b_streamOutIndex, self.b_targetAddress, self.b_scanRate, self.b_samplesToWrite, self.y_values)
        # ErrorCheck(err, "LJM_PeriodicStreamOut")

    # Step 8) Sets sends positional commands to
    def init_start_positions(self):
        # start position = (x_min, y_static)
        if self.scanType == "X":
            rc = ljm.eWriteNames(self.handle, 2, [self.x_address, self.y_address], [self.x_min, self.y_static])

        # start position = (x_static, y_min)
        elif self.scanType == "Y":
            rc = ljm.eWriteNames(self.handle, 2, [self.x_address, self.y_address], [self.x_static, self.y_min])

        # start position = (x_min, y_min)
        elif self.scanType == "XY":
            rc = ljm.eWriteNames(self.handle, 2, [self.x_address, self.y_address], [self.x_min, self.y_min])

    # Step 9) Actual scan is done here
    def start_scan(self):

        start_time = time.time()

        # Step 1) BEFORE SCAN: Start buffer stream (y axis galvo will start moving now)
        err = ljm.eStreamStart(self.handle, self.b_scansPerRead, self.b_nrAddresses, self.b_aScanList, self.b_scanRate)
        # ErrorCheck(err, "LJM_eStreamStart");

        # Step 2) DO SCAN: Send all scan commands to galvo/servo
        rc = ljm.eWriteNames(self.handle, len(self.aAddresses), self.aAddresses, self.aValues)

        # Step 3) AFTER SCAN: Terminate stream of sine wave. This means that the buffer will stop looping/changing value
        err = ljm.eStreamStop(self.handle)
        # ErrorCheck(err, "Problem closing stream");

        # Step 4) sends stop commands to galvo/servo by setting voltage from labjack to servos to 0V
        rc = ljm.eWriteNames(self.handle, 2, [self.x_address, self.y_address], [0, 0])

        end_time = time.time()
        print("Actual scan time:", end_time - start_time)

    # __________ POST SCAN FUNCTIONS __________

    # After scan, collect feedback values from buffer (if we configure sampling)
    def sample_feedback_from_buffer(self):
        """After scan is done, we want """
        data = {'t': [], 'x_in': [], 'y_in': [], 'x_out': [], 'y_out': []}
        data['x_in'] = self.x_values
        data['y_in'] = self.y_values

        # TODO: get feedback values from buffer and save them to dict 'data'

        return data

    # Terminates labjack connection
    def close_labjack_connection(self):
        print("Closing labjack connection")
        err = ljm.close(self.handle)
        if err != 0:
            print("Problem closing T7 device")
        # ErrorCheck(err, "Problem closing device");


class Management:
    # Get date and time
    curr_date = date.today().strftime("%y%m%d")  # required: from datetime import date
    curr_time = time.strftime("%Hh %Mm", time.localtime())

    def manage_local_files(self, filename, data):
        # OLD FILE NAME = f'{scan_name}_[{x_dim},{y_dim}]_[x,y]_{x_lim}_x_lim_{y_amp}_amp_{y_freq}_yfreq__bias_{bias}uA_{cts}kHz_Cts_{today}'  # where scan_name = '68_LV_0mA'

        # Create date folder
        if not os.path.exists(f'K:\\Microscope\\Data\\{self.curr_date}'):
            os.makedirs(f'K:\\Microscope\\Data\\{self.curr_date}')

        # Create measurement folder within date folder
        os.makedirs(f'K:\\Microscope\\Data\\{self.curr_date}\\Scan_{self.curr_time}')

        # Create file to save processed data
        file_output = open(f"K:\\Microscope\\Data\\{self.curr_date}\\Scan_{self.curr_time}\\{filename}.txt", "w")

        # Save data (x,y,t for now)
        self.save_data(data, file_output)

    def save_data(self, data, data_file):
        # Saving info about scan, which parameters, time taken, anything else we want to save for later review
        txt_in_file = ""  # TODO: decide if and what text we want in our file
        data_file.write(f"{txt_in_file}\n")
        data_file.write(f"\n"
                        f"x_in, y_in are theoretical values that are sent to servos\n"
                        f"x_out, y_out are measured values that are sampled from servos\n")

        data_file.write("DATA: \n        t       |       x_in       |       y_in       |       x_out       |       y_out        \n")
        for j in range(len(data['t'])):
            str_row_j = str(data['t'][j]) + " | " + str(data['x_in'][j]) + " | " + str(data['y_in'][j]) + " | " + str(data_file.write(str_row_j))

        data_file.close()

    def save_mat_fig(self, fig, name, curr_date, curr_time):
        file = open(f'K:\\Microscope\\Data\\{curr_date}\\Scan_{curr_time}\\{name}.mpl', 'wb')
        pickle.dump(fig, file)
        file.close()
        # https://stackoverflow.com/questions/67538039/python-equivalent-of-fig-file-from-matlab?noredirect=1&lq=1

    def open_mat_fig(self, name, curr_date, curr_time):
        # ------- HOW TO OPEN PREVIOUS FIG FILE ------
        # fig_name = "fig_test_open"
        # open_mat_fig(fig_name)

        # https://stackoverflow.com/questions/67538039/python-equivalent-of-fig-file-from-matlab?noredirect=1&lq=1
        open_file = open(f'K:\\Microscope\\Data\\{curr_date}\\Scan_{curr_time}\\{name}.mpl', 'rb')
        open_figure = pickle.load(open_file)
        open_figure.show()


class Plotting:

    def plot_theoretical(self):

        all_times, all_x_vals, all_y_vals = self.getAllTimes()

        # PLOTTING TIMES:
        # self.plot_times(all_times)
        # PLOTTING X:
        self.plot_x(all_times, all_x_vals)
        # PLOTTING Y:
        self.plot_y(all_times, all_y_vals)
        # PLOTTING X AND Y:
        self.plot_xy(all_times, all_x_vals, all_y_vals)

        plt.show()

    def getAllTimes(self): # FOR PLOTTING
        all_times = []
        all_x_vals = []
        all_y_vals = []

        # get theoretical times for full scan (based on single period times)
        for i in range(len(t7.single_x_times)):    # for each sweep, i.e. x step
            x_time_offset = t7.single_x_times[i]
            x = t7.x_values[i]

            n_sweep = int(t7.b_samplesToWrite/2)   # int(len(t7.single_y_times)/2)
            for j in range(n_sweep):  # only for one sweep
                y_time_offset = t7.single_y_times[j]

                if i%2 == 0:
                    y = t7.y_values[j]
                else:
                    y = t7.y_values[j+n_sweep]

                all_times.append(x_time_offset + y_time_offset)
                all_x_vals.append(x)
                all_y_vals.append(y)

        return all_times, all_x_vals, all_y_vals

    def plot_times(self, all_times):
        plt.figure("T_thx")
        plt.plot(t7.single_x_times, 'b.')
        plt.xlabel("n")
        plt.ylabel("single times for X")
        plt.grid()
        plt.title(f"Single time X \nScantype={t7.scanType}")

        plt.figure("T_thy")
        plt.plot(t7.single_y_times, 'b.')
        plt.xlabel("n")
        plt.ylabel("single times for Y")
        plt.grid()
        plt.title(f"Single time Y \nScantype={t7.scanType}")

        plt.figure("T_thxy")
        plt.plot(all_times, 'b.')
        plt.xlabel("n")
        plt.ylabel("all times for X and Y")
        plt.grid()
        plt.title(f"TOTAL TIME \nScantype={t7.scanType}")

    def plot_x(self, all_times, all_x_vals):
        plt.figure("X_th")
        plt.plot(t7.single_x_times, t7.x_values, 'b.')
        plt.xlabel("time [s]")
        plt.ylabel("x input voltage [V]")
        plt.grid()
        self.maybe_plot_limits(plt_x=True, t_f=t7.single_x_times[-1])
        plt.title(f"[x]  Iterated step values \nScantype={t7.scanType}")

        plt.figure("X_sc")
        plt.plot(all_times, all_x_vals, 'b.')
        plt.plot(all_times, all_x_vals, 'b--')
        plt.xlabel("time [s]")
        plt.ylabel("x input voltage [V]")
        plt.grid()
        self.maybe_plot_limits(plt_x=True, t_f=all_times[-1])
        plt.title(f"[x]  Full scan path \nScantype={t7.scanType}")

    def plot_y(self, all_times, all_y_vals):
        plt.figure("Y_th")
        plt.plot(t7.single_y_times, t7.y_values, 'r')
        plt.xlabel("time [s]")
        plt.ylabel("y input voltage [V]")
        plt.grid()
        self.maybe_plot_limits(plt_y=True, t_f=t7.single_y_times[-1])
        plt.title(f"[y]  Values for one period \nScantype={t7.scanType}")

        plt.figure("Y_sc")
        plt.plot(all_times, all_y_vals, 'r')
        plt.xlabel("time [s]")
        plt.ylabel("y input voltage [V]")
        plt.grid()
        self.maybe_plot_limits(plt_y=True, t_f=all_times[-1])
        plt.title(f"[y]  Full scan path \nScantype={t7.scanType}")

    def plot_xy(self, all_times, all_x_vals, all_y_vals):
        plt.figure("XY_sc")
        plt.plot(all_x_vals, all_y_vals, 'g.')
        plt.plot(all_x_vals, all_y_vals, 'g--')
        plt.xlabel("X input voltage [V]")
        plt.ylabel("Y input voltage [V]")
        plt.grid()
        self.maybe_plot_limits(plt_x=True, plt_y=True, t_f=all_times[-1])
        plt.title(f"[x vs. y]  Full scan path \nScantype={t7.scanType}")

    def maybe_plot_limits(self, t_f, plt_x=False, plt_y=False):

        if t7.x_max > 3 or t7.y_max > 2:
            if plt_x and plt_y:
                plt.plot([-5, 5], [-5,-5], 'k--')
                plt.plot([-5, 5], [5, 5], 'k--')
                plt.plot([-5, -5], [-5, 5], 'k--')
                plt.plot([5, 5], [-5, 5], 'k--')

            elif plt_x or plt_y:
                plt.plot([0, t_f], [-5, -5], 'k--')
                plt.plot([0, t_f], [5, 5], 'k--')

    def plot_data(self):
        pass
        # TODO: create and save figures
        # fig, name = plot_...()
        # save_mat_fig(fig, name, curr_date, curr_time)

    def turtle_figure(self, values):
        window = ttl.Screen()
        myPen = ttl.Turtle()
        self.config_turtle(window, myPen, values)

        for i in range(0, len(values)):
            x = values[i][1] * 2000
            y = (0.01 + values[i][2]) * 40000
            myPen.goto(x, y)
            myPen.pendown()
            # myPen.getscreen().update()   # not needed

        time.sleep(11)  # Needed since turtle window disappears otherwise ... i think

    def config_turtle(self, window, myPen, values):
        window.bgcolor("#FFFFFF")
        myPen.hideturtle()
        # turtle.setworldcoordinates(-1, -1, 20, 20)
        # myPen.tracer(0)
        myPen.speed(0)
        myPen.pensize(3)
        myPen.color("#AA00AA")
        myPen.penup()
        myPen.goto(1, 110)

        minx = 1000000
        maxx = -1000000
        miny = 1000000
        maxy = -1000000
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
        # window.setworldcoordinates(minx, miny, maxx, maxy)

# ____________ MAIN ______________________
# NOTE: Repeatability = 10 [µrad] ≈ 0.0006 [degrees]   https://www.thorlabs.de/newgrouppage9.cfm?objectgroup_id=14132&pn=QS7XY-AG
# x_angle =>  max X deflection angle  (mehcanical or optical???)  note: The optical angle is 2 times the mechanical angle
# y_angle =>  max Y deflection angle  (mehcanical or optical???)
# x_steps =>  Must be in valid range =~ {10-10000}      WARNING: MAXIMUM X_STEPS == (x_angle)/0.0006
    #  -->  xsteps = 100    -->   d_angle =~ 0.05 degrees
    #  -->  xsteps = 1000   -->   d_angle =~ 0.005 degrees
    #  -->  xsteps = 10000  -->   d_angle =~ 0.0005 degrees


# X is variable, Y is static
class X:
    x_angle = 3
    y_angle = 3

    x_steps = 10
    y_static = 0
    scan_type = "X"
    filename = "some_filename"


# X is static, Y is variable
class Y:
    x_angle = 3
    y_angle = 3

    x_steps = 10
    x_static = 0
    y_frequency = 0.5
    scan_type = "Y"
    filename = "some_filename"


# X is variable, Y is variable
class XY:
    x_angle = 3
    y_angle = 3

    x_steps = 10
    y_frequency = 0.5
    scan_type = "XY"
    filename = "some_filename"


if __name__ == '__main__':
    # WARNING!!! To double-check, print out all x and y voltage values before running it for first time!!!

    # 1) Initiates labjack class
    t7 = T7(param=XY(), scanForm="raster", record=False, pingQTag=False)
    # scanForm --> { "raster" , "lissajous",  "saw-sin" }

    # 2) Prepare and perform scan
    noError = t7.main_galvo_scan()

    # 3) After scan, sample feedback values and save to file
    if noError:
        pass
        # 3.1) Stream values from buffer
        # data = t7.sample_buffer()

        # 3.2) Save data
        # Management.manage_local_files(t7.filename, data)

        # 3.3) Plot data figures with sampled data
        # Plotting.plot_data()

    # 4) Terminates labjack connection  (note: labjack device only opened if scan wasn't aborted prematurely)
    if t7.handle is not None :
        t7.close_labjack_connection()
    else:
        print("T7 not opened --> will not be closed")


"""
TODO:
- use "@property" in front of relevant functions
- also use "typing"/hinting for what every function takes in and returns

- print out all x and y voltage values before running it for first time!!! 
- calculate and fill in sample rate in function: "check_samplerate()"
- check how many y_values we can fit in a buffer, max 512 (16-bit samples)
- fill in Qutag addresses (need to do this before we can connect to Qutag server)
- try to move eStreamStart command into the buffer stream to get proper timing --> populate_lists()
- try to move eStreamStart command into the buffer stream, it would be nice to have everything in one place --> populate_lists()

- look into function "socket_connection()" and maybe make nicer
- maybe add more safety checks
- finish writing this when we want to start sampling values!
- draw theoretical scan path with turtle
- draw sampled data scan path
- Question: can we start SSPD code from this file so we don't need to manually start both? 
- ask carol what frequency range is ok
- create conversion table: FOV (um) to voltage input 
- use smoothed step function to prevent harsh jumps/steps (labjack signal gen)
- find the "ErrorCheck" function and maybe use it here
"""

"""
You could stream out the DIO states using a register such as DIO_STATE. Alternatively, something like our Pulse output DIO_EF may be useful:
https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/1324-pulse-out-t-series-datasheet/

maxSampleRate = 100000 / numChannels
I would recommend seeing the information in our stream documentation for other stream out details:
https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/32-stream-mode-t-series-datasheet/#section-header-two-ebb7e
"""

"""
self.scanTime = 0

# Broundary parameters:-----------
self.x_angle = 0
self.y_angle = 0
self.x_steps = 0
self.x_min = 0
self.x_max = 0
self.y_min = 0
self.y_max = 0

# "X" VARIABLES:-----------
self.y_static = 0
self.x_delay = 0
# "Y" VARIABLES:-----------
self.y_waveform = ''
self.y_frequency = 0
self.x_static = 0
# "XY" VARIABLES:-----------
self.y_waveform = ''
self.y_frequency = 0

# "X" HARDCODED: -----------
#self.y_waveform = ''
self.b_samplesToWrite = 0
self.b_scanRate = 0
# 'sine' --> "Y" ,"XY" HARDCODED:-----------
self.y_steps = 0
self.y_phase = 0
self.y_period = 0
self.x_delay = 0
self.b_samplesToWrite = 0
self.b_scanRate = 0
self.b_scansPerRead = 0 

# "X" UNUSED:       self.x_static = self.y_frequency = self.y_period = self.y_steps = None
# "Y" UNUSED:       self.y_static = None
# "XY" UNUSED:      self.x_static = self.y_static = None
"""
