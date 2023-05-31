import time
from datetime import date, datetime
from labjack import ljm  # I think this requires that we have the labjack folder in our dir for access

# import ljm_stream_util
import struct
import socket
import pickle
import numpy as np
import matplotlib.pyplot as plt
import os
import turtle as ttl


# UPDATED: 25/5-2023

def getInputVariableClass(scanType):
    # Call appropriate class to get input parameters
    if scanType == "X":
        return X()
    elif scanType == "Y":
        return Y()
    elif scanType == "XY":
        return XY()
    else:
        return None


class ErrorChecks:

    def check_voltages(self):
        # max is 5V but this gives a bit of margin, NOTE: val = 0.22*optical angle --> val = 1V is big enough for our scope
        max_voltage = 4

        # Checking that max allowed voltage is not changed. 5V is the absolute maximum allowed, but we give some margins
        if max_voltage > 4.5:
            print("Error: to high max voltage, change back to 4.5V")
            t7.abort_scan = True

        # CHECKING INPUT VALUES TO SERVOS
        for x_val in t7.x_values:
            if abs(x_val) > max_voltage:
                print(f"Error: Too large voltage ({x_val}V) found in X list!")
                t7.abort_scan = True
        for y_up in t7.y_values_up:
            if abs(y_up) > max_voltage:
                print(f"Error: Too large voltage ({y_up}V) found in Y up list!")
                t7.abort_scan = True
        for y_down in t7.y_values_down:
            if abs(y_down) > max_voltage:
                print(f"Error: Too large voltage ({y_down}V) found in Y down list!")
                t7.abort_scan = True

    def check_scan_type(self):
        # CHECKING SCAN TYPES
        if t7.scanType not in ["X", "Y", "XY"]:
            print("Error: Invalid scan type provided!")
            t7.abort_scan = True

    def check_y_frequency(self):
        # NOTE: MUST FOLLOW NYQUIST CRITERION --> "Nyquist criterion requires that the sampling frequency be at least twice the highest frequency contained in the signal"
        max_y_freq = 10000  # TODO: calculate a max frequency
        min_y_freq = 0.00001  # TODO: calculate a min frequency

        if (t7.y_frequency < min_y_freq) or (max_y_freq < t7.y_frequency):
            print(f"Error: y_frequency = {t7.y_frequency} is out of bounds!")
            t7.abort_scan = True

    def check_x_steps(self):
        max_x_steps = (t7.x_angle) / 0.0006  # if self.x_angle is optical
        # CHECKING NUMBER OF X STEPS BASED ON REPEATABILITY (= 10 [µrad] ≈ 0.0006 [degrees]) https://www.thorlabs.de/thorproduct.cfm?partnumber=QS7XY-AG
        if (t7.x_steps < 1) or (t7.x_steps > max_x_steps):
            print(f"Error: Too many steps to do in x! (based on repeatability specs)")
            t7.abort_scan = True


class T7:
    # --------------- HARDCODED CLASS CONSTANT BASED ON WIRING -------------
    # Servo and labjack addresses, note: we are using tickDAC
    x_address = "TDAC1"  # "30002"  "FIO1"
    y_address = "TDAC0"  # "30000"  "FIO0"
    wait_address = "WAIT_US_BLOCKING"
    # QuTag addresses
    q_start_address = ""  # marks start of scan               # TODO: FILL IN
    q_stop_address = ""  # marks end of scan                 # TODO: FILL IN
    q_step_address = ""  # marks each change in x value      # TODO: FILL IN

    # TODO: check how many y_values we can fit in a buffer, max 512 (16-bit samples)
    max_buffer_size = 256  # Buffer stream size for y waveform values. --> Becomes resolution of sinewave period waveform == y_steps

    def __init__(self, scanType, scanPattern, pingQuTag=False, plotting=False):
        """
        :param scanType:        Either class instance for scan type or a string in {"X", "Y", "XY"} which could call the class from this init function
        :param scanPattern:     Defines which scan pattern we want  { "raster" , "lissajous",  "saw-sin" }
        :param pingQuTag:       Bool for whether we want to ping the QuTag with the scan { True , False }
        """
        # --------------- ATTRIBUTES ----------------------------------------------------

        self.scanVariables = getInputVariableClass(scanType)  # class for {"X", "Y", "XY"}
        self.filename = self.scanVariables.filename
        self.scanType = scanType  # {"X", "Y", "XY"}
        self.scanPattern = scanPattern  # { "raster" , "lissajous",  "saw-sin" }   # only raster used at the moment
        self.q_pingQuTag = pingQuTag  # bool for whether we want to ping the qutag with the scan { True , False }
        # --------------- PLACEHOLDER VALUES --------------------------------------------
        self.handle = None  # Labjack device handle
        self.abort_scan = False  # Safety bool for parameter check
        self.aAddresses = []  # Scanning plan: list of addresses for all the commands
        # New solution
        self.aValuesUp = []
        self.aValuesDown = []

        self.x_values = []  # List for x values that are set during scan
        self.y_values_up = []
        self.y_values_down = []

        # --------------- PLOTTING -------------------------------------------------------
        self.plotFigures = plotting
        self.single_x_times = []
        self.single_y_times = []

    # MAIN FUNCTION THAT PREPARES AND PERFORMS SCAN
    def main_galvo_scan(self):
        # Step 1) Calculate all scan parameters
        print("\nStep 1) Defining scan parameters.")
        self.get_scan_parameters()

        # Step 2) Get a list of x and y values given scan parameters
        print("\nStep 2) Generating scan x,y values.")
        self.get_x_values()
        self.get_y_values()

        # Step 3) Check all input parameters (and abort if needed)
        print("\nStep 3) Doing safety check on scan parameters.")
        self.auto_check_scan_parameters()

        # Plotting theoretical scan values  -->  maybe remove later:
        if self.plotFigures:
            Plotting().plot_theoretical()

        # Step 3.5) Check to abort  (due to error in "self.auto_check_scan_parameters()")
        print("\nStep 3.5) Check if we need to abort scan.")
        if self.abort_scan:
            print("Error check failed. Aborting scan.")
            return False  # Abort scan due to unacceptable values (if error is raised)
        else:
            print("\nError check succeeded. Continuing scan.")

        # return False  # SAFETY RETURN, TEMP BEFORE WE ACTUALLY CONNECT TO LABJACK

        # Step 4) Open communication with labjack handle
        print("\nStep 4) Opening labjack connection")
        self.open_labjack_connection()

        # Step 5) Opens communication with qu-tag server
        if self.q_pingQuTag:
            print("\nCreating socket connection with Qutag server.")
            self.socket_connection()

        # Step 6) Populates command list with calculated y values and addresses
        print("\nStep Populating command list.")
        # NEW WAY WITHOUT BUFFER:
        self.populate_scan_lists()

        # Step 8) Initiate start position of galvos
        print("\nStep 8) Setting start positions of galvos.")
        self.init_start_positions()
        time.sleep(1)  # wait 1 second to give galvos time to get to start positions

        # Step 9) Perform scan
        print("\nStep 9) (not) Performing scan...")
        self.start_scan()

        return True

    # Step 1) Sets all parameters depending on selected scan pattern and scan type
    def get_scan_parameters(self):
        """Configured for QS7XY-AG galvanometer: https://www.thorlabs.de/newgrouppage9.cfm?objectgroup_id=14132&pn=QS7XY-AG"""

        # Set by user input. Required by all types of scans.
        self.x_angle = self.scanVariables.x_angle
        self.y_angle = self.scanVariables.y_angle
        self.x_steps = self.scanVariables.x_steps

        # SCAN TYPE 1) X is variable, Y is static
        if self.scanType == "X":
            # HARDCODED:
            self.y_waveform = 'static'  # not used atm
            self.x_min = -self.x_angle * 0.22  # Command voltage input to servos:  0.22 [V/°] (optical)
            self.x_max = self.x_angle * 0.22
            self.y_static = self.y_angle * 0.22
            self.x_delay = 10 / self.x_steps  # hardcoded to a 10 seconds scan:  x_delay[s/step] = (10[s])/(x_steps[step]) # TODO: y is static so x_delay is not dependent on a period --> set this value to something reasonable
            # UNUSED:   self.x_static, self.y_frequency, self.y_period, y_phase, self.y_min, self.y_max

        # SCAN TYPE 2) X is static, Y is variable
        elif self.scanType == "Y":
            # INPUT VARIABLES:  # parameters selected by user (at bottom of file) given is Hz
            self.y_frequency = self.scanVariables.y_frequency
            # HARDCODED:
            self.y_waveform = 'sine'
            self.x_static = self.x_angle * 0.22  # Command voltage input to servos:  0.22 [V/°] (optical)
            self.y_min = -self.y_angle * 0.22
            self.y_max = self.y_angle * 0.22
            # UNUSED:  self.y_static, self.x_min, self.x_max

        #  SCAN TYPE 3) X is variable, Y is variable
        elif self.scanType == "XY":
            # INPUT VARIABLES:  # parameter selected by user (at bottom of file) given is Hz
            self.y_frequency = self.scanVariables.y_frequency
            # HARDCODED:
            self.y_waveform = 'sine'
            self.x_min = -self.x_angle * 0.22  # Command voltage input to servos:  0.22 [V/°] (optical)
            self.x_max = self.x_angle * 0.22
            self.y_min = -self.y_angle * 0.22
            self.y_max = self.y_angle * 0.22
            # UNUSED:   self.x_static, self.y_static

        if self.y_waveform == 'sine':  # for scantype "Y" and "XY"
            # HARDCODED:
            self.y_phase = np.pi / 2
            self.y_period = 1 / self.y_frequency
            self.x_delay = self.y_period / (2)  # time between every X command. Should be half a period (i.e. time for one up sweep)

        # Buffer stream variables:
        self.b_samplesToWrite = self.max_buffer_size  # = how many values we save to buffer stream = y_steps = resolution of one period of sinewave, --> sent to TickDAC --> sent to y servo input
        self.b_scanRate = int(self.b_samplesToWrite / (
                    2 * self.x_delay))  # scanrate = scans per second = samples per second for one address = (resolution for one sine period)/(one sine period)   NOTE: (2*self.x_delay) = self.y_period (of sinewave)
        #self.b_scansPerRead = int(
            #s#elf.b_scanRate / 2)  # NOTE: When performing stream OUT with no stream IN, ScansPerRead input parameter to LJM_eStreamStart is ignored. https://labjack.com/pages/support/?doc=%2Fsoftware-driver%2Fljm-users-guide%2Festreamstart
        self.y_delay = 1 / (self.b_samplesToWrite / (2 * self.x_delay)) # self.b_scanRate  # time between each y value in stream buffer
        print(self.y_delay)
        # Expected scan time:
        self.scanTime = self.x_steps * self.x_delay  # Note: it will be slightly higher than this which depends on how fast labjack can iterate between commands
        print(f"Expected scan time = {int(self.scanTime)} seconds")

    # Step 2) Returns a list of x values that the scan will perform
    def get_x_values(self):
        # Create list for x values (ONLY ONE COLUMN) we send as command to servo motor to set --> units: maybe voltage?

        # If we want to step x values
        if self.scanType == 'X' or self.scanType == 'XY':
            # populating "x_values" list with discrete values
            x_step_size = (self.x_max - self.x_min) / self.x_steps  # step size of our x values
            k = self.x_min
            # x_values.append(k)
            for i in range(self.x_steps):
                self.x_values.append(round(k, 10))
                self.single_x_times.append(i * self.x_delay)  # for plotting
                k += x_step_size
        elif self.scanType == 'Y':
            # populating "x_values" list with x_Static a number of times ( == self.x_steps)
            for i in range(self.x_steps):
                self.x_values.append(round(self.x_static, 10))
                self.single_x_times.append(i * self.x_delay)  # for plotting
        else:
            print("Error in get x values! Invalid scan type given.")
            self.abort_scan = True

    # Step 2) Returns a list of y values that the scan will perform
    def get_y_values(self):
        # if we are only changing x then the buffer only needs one value --> Y STATIC
        if self.scanType == 'X':
            # in this case: self.y_waveform == 'constant'
            for i in range(int(self.b_samplesToWrite / 2)):
                self.y_values_up.append(round(self.y_static, 10))
                self.single_y_times.append(i * self.y_delay)  # for plotting

            for i in range(int(self.b_samplesToWrite / 2), int(self.b_samplesToWrite)):
                self.y_values_down.append(round(self.y_static, 10))
                self.single_y_times.append(i * self.y_delay)  # for plotting

        elif self.scanType == 'Y' or self.scanType == 'XY':
            # if Y has periodic waveform:
            t_curr = 0
            t_step_size = self.y_period / self.b_samplesToWrite
            n_half_period = int(self.b_samplesToWrite / 2)

            single_y_times_up = []  # for plotting
            single_y_times_down = []  # for plotting

            if self.y_waveform == 'sine':
                for i in range(n_half_period):
                    t_curr = i * self.y_delay
                    single_y_times_up.append(t_curr)  # for plotting
                    single_y_times_down.append(t_curr + (self.y_period / 2))  # for plotting

                    y_curr = self.y_max * np.sin((2 * np.pi * self.y_frequency * t_curr) - self.y_phase)
                    self.y_values_up.append(round(y_curr, 10))
            else:
                print("Error defining waveform for Y")
                self.abort_scan = True
                return

            self.y_values_down = self.y_values_up.copy()
            self.y_values_down.reverse()
            self.single_y_times = single_y_times_up + single_y_times_down  # FOR PLOTTING
            print("Y up sweep  ", self.y_values_up)
            print("Y down sweep", self.y_values_down)

        else:
            print("Error in get_y_values! Invalid scan type given.")
            self.abort_scan = True

    # Step 3) Error checks
    def auto_check_scan_parameters(self):

        # TODO CHECKS/NOTE:
        #   - TDAC can update it's value once every ~ 1ms (a frequency of 1000Hz) --> consider if this is too low!
        #       --> self.y_delay > 1  (ms)

        # MOST IMPORTANT SO WE DON'T DAMAGE DEVICE
        ErrorChecks().check_voltages()  # CHECKING INPUT VALUES TO SERVOS

        # USEFUL CHECKS TO ENSURE THAT SCAN IS SUCCESSFUL
        ErrorChecks().check_scan_type()  # CHECKING SCAN TYPES
        ErrorChecks().check_x_steps()  # CHECKING NUMBER OF X STEPS BASED ON REPEATABILITY
        # err.check_samplerate()  # CHECKING MAX SAMPLE RATE  # maxSampleRate = 100000 / numChannels   and we likely have under 10 channels (~6-7)
        if self.scanType in ["Y", "XY"]:
            ErrorChecks().check_y_frequency()  # CHECKING Y FREQUENCY

    # Step 4) Connect to labjack device
    def open_labjack_connection(self):
        self.handle = ljm.openS("T7", "ANY", "ANY")  # ErrorCheck(self.handle, "LJM_Open")
        info = ljm.getHandleInfo(self.handle)  # ErrorCheck(info, "PrintDeviceInfoFromHandle")
        print(
            f"Opened a LabJack with Device type: {info[0]}, Connection type: {info[1]},\n Serial number: {info[2]}, IP address: {ljm.numberToIP(info[3])}, Port: {info[4]},\nMax bytes per MB: {info[5]} \n")

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
    def populate_scan_lists(self):

        # Add half period y values to command list
        # Add delay (can be different delays for different lists) and one value at a time to list

        # "Delays for x microseconds. Range is 0-100000.
        wait_delay = self.y_delay*1000000
        for up_val in self.y_values_up:
            self.aAddresses += [self.y_address, self.wait_address]
            self.aValuesUp += [up_val, wait_delay]

        for down_val in self.y_values_down:
            self.aValuesDown += [down_val, wait_delay]

        # PRINTING IN CONSOLE
        # print(f"\n-------aValuesUp--------|-------aValuesDown------|-----------aAddresses-----------")
        # for i in range(0, len(self.aAddresses), 2):
        #    print(f"  {self.aAddresses[i]}: {self.aValuesUp[i]},     {self.aAddresses[i]}: {self.aValuesDown[i]},    {self.aAddresses[i+1]}: {self.aValuesUp[i+1]}")

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
        if self.q_pingQuTag:
            # Send start marker to qtag (maybe add time delay or other info to qtag)
            rc = ljm.eWriteNames(self.handle, 3, [self.q_start_address, self.wait_address, self.q_start_address],
                                 [1, self.x_delay, 0])

        # Step 2) DO SCAN: Send all scan commands to galvo/servo
        # NEW SOLUTION WITHOUT BUFFER:
        for i in range(0, len(self.x_values), 2):  # range(start=0, stop=len(self.x_values), step=2):
            rc = ljm.eWriteNames(self.handle, len(self.aAddresses) + 1, self.aAddresses + [self.x_address],
                                 self.aValuesUp + [self.x_values[i]])
            rc = ljm.eWriteNames(self.handle, len(self.aAddresses) + 1, self.aAddresses + [self.x_address],
                                 self.aValuesDown + [self.x_values[i + 1]])

        # Step 3) AFTER SCAN: Terminate stream of sine wave. This means that the buffer will stop looping/changing value
        if self.q_pingQuTag:
            # Send end marker to qtag (maybe add time delay or other info to qtag)
            rc = ljm.eWriteNames(self.handle, 3, [self.q_stop_address, self.wait_address, self.q_stop_address],
                                 [1, self.x_delay, 0])

        # Step 4) sends stop commands to galvo/servo by setting voltage from labjack to servos to 0V
        rc = ljm.eWriteNames(self.handle, 2, [self.x_address, self.y_address], [0, 0])

        end_time = time.time()
        print("Actual scan time:", end_time - start_time)

    # __________ POST SCAN FUNCTIONS __________

    # After scan, collect feedback values from buffer (if we configure sampling)
    def sample_feedback_from_buffer(self):
        """After scan is done, we want """
        data = {'t': [], 'x_in': [], 'y_in': [], 'x_out': [], 'y_out': []}
        # data['x_in'] = self.x_values
        # ...
        # TODO: get feedback values from buffer and save them to dict 'data'
        # ljm.eStreamRead
        return data

    # Terminates labjack connection
    def close_labjack_connection(self):
        print("Closing labjack connection...")
        if self.handle is None:
            print("\nT7 was not opened and therefore doesn't need closing")
        else:
            time.sleep(1)  # don't close too fast, just in case there is still something being transmitted
            err = ljm.close(self.handle)
            if err is None:
                print("Closing successful.")
            else:
                print("Problem closing T7 device. Error =", err)

    def TestWriteToLabJack(self):
        # TROUBLESHOOTING: TESTING WRITE NAMES TO LABJACK
        names = ["TDAC0", "TDAC1"]
        v = np.linspace(0, 0.1, 20)

        for e in v:
            aValues = [0, e]  # [2.5 V, 12345]
            err = ljm.eWriteNames(self.handle, len(names), names, aValues)
            print("Error =", err)
            time.sleep(0.1)
            print(e)


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
        data_file.write(
            "DATA: \n        t       |       x_in       |       y_in       |       x_out       |       y_out        \n")
        for j in range(len(data['t'])):
            str_row_j = str(data['t'][j]) + " | " + str(data['x_in'][j]) + " | " + str(data['y_in'][j]) + " | " + str(
                data['x_out'][j]) + " | " + str(data['y_out'][j])
            data_file.write(str_row_j)
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

        grid = plt.GridSpec(2, 4, wspace=0.4, hspace=0.3)
        if t7.scanType == 'X':
            plt.suptitle(f"PARAMETERS:      [scan_type={t7.scanType}]      [x_steps={t7.x_steps}]      [x_angle={t7.x_angle}]      [y_angle={t7.y_angle}]\n ----------------------------------------------------------------------------------------------------------------------------------------------")
        else:
            plt.suptitle(f"PARAMETERS:      [scan_type={t7.scanType}]      [x_steps={t7.x_steps}]      [x_angle={t7.x_angle}]      [y_angle={t7.y_angle}]      [frequency={t7.y_frequency}]\n ----------------------------------------------------------------------------------------------------------------------------------------------")

        ax_x_1 = plt.subplot(grid[0, 0])
        ax_y_1 = plt.subplot(grid[0, 1])
        ax_x_2 = plt.subplot(grid[1, 0])
        ax_y_2 = plt.subplot(grid[1, 1])
        ax_xy = plt.subplot(grid[:, 2:])

        # PLOTTING TIMES:
        # self.plot_times(all_times)
        # PLOTTING X:
        self.plot_x(all_times, all_x_vals, ax_x_1, ax_x_2)
        # PLOTTING Y:
        self.plot_y(all_times, all_y_vals, ax_y_1, ax_y_2)
        # PLOTTING X AND Y:
        self.plot_xy(all_times, all_x_vals, all_y_vals, ax_xy)

        plt.show()

    def getAllTimes(self):  # FOR PLOTTING
        all_times = []
        all_x_vals = []
        all_y_vals = []

        # get theoretical times for full scan (based on single period times)
        for i in range(len(t7.single_x_times)):  # for each sweep, i.e. x step
            x_time_offset = t7.single_x_times[i]
            x = t7.x_values[i]

            for j in range(int(t7.b_samplesToWrite / 2)):
                y_time_offset = t7.single_y_times[j]

                if i % 2 == 0:
                    y = t7.y_values_up[j]
                else:
                    y = t7.y_values_down[j]

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

    def plot_x(self, all_times, all_x_vals, ax_single, ax_full):
        # plt.figure("X_th")
        ax_single.plot(t7.single_x_times, t7.x_values, 'r.', label="X step values")
        ax_single.set(xlabel="time [s]")
        ax_single.set(ylabel="x command voltage [V]")
        # ax_single.set(grid()
        self.maybe_plot_limits(ax=ax_single, plt_x=True, t_f=t7.single_x_times[-1])
        ax_single.set(title=f"[X vs. time]  \nX step values")
        #ax_single.legend(bbox_to_anchor=(0.01, 0.99), loc='upper left', borderaxespad=0.)

        # plt.figure("X_sc")
        ax_full.plot(all_times, all_x_vals, 'y--', label="step transition") # b
        ax_full.plot(all_times, all_x_vals, 'r.', label="X command voltage")
        ax_full.set(xlabel="time [s]")
        ax_full.set(ylabel="x command voltage [V]")
        ax_full.legend(bbox_to_anchor=(0.01, 0.99), loc='upper left', borderaxespad=0.)
        # ax_full.set(grid()
        self.maybe_plot_limits(ax=ax_full, plt_x=True, t_f=all_times[-1])
        ax_full.set(title=f"[X vs. time]  \nComplete X scan path")

    def plot_y(self, all_times, all_y_vals, ax_single, ax_full):
        # plt.figure("Y_th")
        # plt.plot(t7.single_y_times, t7.y_values_up + t7.y_values_down , 'r')
        ax_single.plot(t7.single_y_times[:len(t7.y_values_up)], t7.y_values_up, 'c', label="Y up sweep")
        ax_single.plot(t7.single_y_times[len(t7.y_values_up):], t7.y_values_down, 'b', label="Y down sweep")
        ax_single.set(xlabel="time [s]")
        ax_single.set(ylabel="y command voltage [V]")
        ax_single.legend() #bbox_to_anchor=(0.01, 0.99), loc='upper left', borderaxespad=0.)
        # ax_single.grid()
        self.maybe_plot_limits(ax=ax_single, plt_y=True, t_f=t7.single_y_times[-1])
        ax_single.set(title=f"[Y vs. time]  \nOne period of Y sine wave")

        # plt.figure("Y_sc")
        col = 'k'
        halfPeriodIndex = int(t7.b_samplesToWrite/2)
        for i in range(int(2*len(all_y_vals)/t7.b_samplesToWrite)): # how many sweeps we do
            if i%2:
                col = 'b'
            else:
                col = 'c'
            ax_full.plot(all_times[i*halfPeriodIndex:(i+1)*halfPeriodIndex], all_y_vals[i*halfPeriodIndex:(i+1)*halfPeriodIndex], col)

        ax_full.plot(all_times[0:2], all_y_vals[0:2], 'c', label="Y up sweep")
        ax_full.plot(all_times[halfPeriodIndex:2+halfPeriodIndex], all_y_vals[halfPeriodIndex:2+halfPeriodIndex], 'b', label="Y down sweep")
        #ax_full.legend(bbox_to_anchor=(0.01, 0.99), loc='upper left', borderaxespad=0)
        #ax_full.plot(all_times, all_y_vals, 'r', label="Y voltage output")
        ax_full.set(xlabel="time [s]")
        ax_full.set(ylabel="y command voltage [V]")
        # ax_full.grid()
        self.maybe_plot_limits(ax=ax_full, plt_y=True, t_f=all_times[-1])
        ax_full.set(title=f"[Y vs. time]  \nComplete Y scan path")

    def plot_xy(self, all_times, all_x_vals, all_y_vals, ax_full):
        # plt.figure("XY_sc")
        ax_full.plot(all_x_vals, all_y_vals, 'y--', label="x step transition") # g
        ax_full.plot(all_x_vals, all_y_vals, 'g.', label="dual-axis command voltage")
        ax_full.set(xlabel="X command voltage [V]")
        ax_full.set(ylabel="Y command voltage [V]")
        ax_full.legend(bbox_to_anchor=(0.7, 1.005), loc='lower left', borderaxespad=0)

        # ax_full.grid()
        self.maybe_plot_limits(ax=ax_full, plt_x=True, plt_y=True, t_f=all_times[-1])
        ax_full.set(title=f"[X vs. Y]  \nComplete dual-axis scan path")

    def maybe_plot_limits(self, ax, t_f, plt_x=False, plt_y=False):
        x_max = max(t7.x_values)
        y_max = max(t7.y_values_up + t7.y_values_down)

        if x_max > 2.5 or y_max > 2.5:
            if plt_x and plt_y:
                ax.plot([-5, 5], [-5, -5], 'k--')
                ax.plot([-5, 5], [5, 5], 'k--')
                ax.plot([-5, -5], [-5, 5], 'k--')
                ax.plot([5, 5], [-5, 5], 'k--')

            elif plt_x or plt_y:
                ax.plot([0, t_f], [-5, -5], 'k--')
                ax.plot([0, t_f], [5, 5], 'k--')

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
"""
NOTE: Repeatability = 10 [µrad] ≈ 0.0006 [degrees]   https://www.thorlabs.de/newgrouppage9.cfm?objectgroup_id=14132&pn=QS7XY-AG
    x_angle =>  max X deflection angle  (mechanical or optical???)  note: The optical angle is 2 times the mechanical angle
    y_angle =>  max Y deflection angle  (mechanical or optical???)
    x_steps =>  valid range =~ {10-10000}  WARNING: MAXIMUM X_STEPS == (x_angle)/0.0006
        -->  x_steps = 100    -->   d_angle =~ 0.05 degrees
        -->  x_steps = 1000   -->   d_angle =~ 0.005 degrees
        -->  x_steps = 10000  -->   d_angle =~ 0.0005 degrees
"""


class X:
    """X is variable, Y is static"""
    filename = 'some_filename'
    x_angle = 1  # MAX    X ANGLE:  Valid range = [-22.5, 22.5]
    y_angle = 1  # STATIC Y ANGLE:  Valid range = [-22.5, 22.5]
    x_steps = 10  # Valid range =~ {1-10000}  WARNING: MAXIMUM X_STEPS == (x_angle)/0.0006


class Y:
    """X is static, Y is variable"""
    filename = 'some_filename'
    x_angle = 3  # STATIC X ANGLE:  Valid range = [-22.5, 22.5]
    y_angle = 1  # MAX    Y ANGLE:  Valid range = [-22.5, 22.5]
    x_steps = 10  # Valid range =~ {1-10000}  WARNING: MAXIMUM X_STEPS == (x_angle)/0.0006
    y_frequency = 0.5


class XY:
    """X is variable, Y is variable"""
    filename = 'some_filename'
    x_angle = 10  # MAX X ANGLE:  Valid range = [-22.5, 22.5]
    y_angle = 3  # MAX Y ANGLE:  Valid range = [-22.5, 22.5]
    x_steps = 50  # Valid range =~ {1-10000}  WARNING: MAXIMUM X_STEPS == (x_angle)/0.0006
    y_frequency = 2


if __name__ == '__main__':

    # 1) Initiates labjack class
    '''
    :param scanType:        Defines which scan type class we call, choose from: {'X', 'Y', 'XY'}
    :param scanPattern:     Defines which scan pattern we want, choose from: {'raster', 'lissajous', 'saw-sin'}  # note: currently only focusing on raster
    :param pingQuTag:       Bool for whether we want to ping the QuTag with the scan, choose from: { True , False } c# note: "pingQuTag" previously called "record"
    :param plotting:        Bool for whether we want to plot input data, choose from: { True , False }
    '''
    t7 = T7(scanType='XY', scanPattern='raster', pingQuTag=False, plotting=True)

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
    t7.close_labjack_connection()

"""
Good book: 
"Experimental Physics: Principles and Practice for the Laboratory"
https://books.google.se/books?id=-svXDwAAQBAJ&pg=SA8-PA67&lpg=SA8-PA67&dq=labjack+python+anaconda&source=bl&ots=GkoE1BKV0W&sig=ACfU3U3Yi0fPQvshzXh6d_7hLQOQ5qttMQ&hl=en&sa=X&ved=2ahUKEwjp_anno4v_AhVcSvEDHUlhB3IQ6AF6BAgtEAM#v=onepage&q=labjack%20python%20anaconda&f=false

TODO:
- look into: 
    device_id = device.get('device_id', '')
    sample_rate = device.get('sample_rate', 0)
    read_rate = device.get('read_rate', 0)
    (source: https://python.hotexamples.com/examples/labjack.ljm/-/eStreamStart/python-estreamstart-function-examples.html)

- NOTE: MUST FOLLOW NYQUIST CRITERION
    --> "Nyquist criterion requires that the sampling frequency be at least twice the highest frequency contained in the signal"

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
From Labjack email:
----
"You could stream out the DIO states using a register such as DIO_STATE. Alternatively, something like our Pulse output DIO_EF may be useful:
https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/1324-pulse-out-t-series-datasheet/
maxSampleRate = 100000 / numChannels
I would recommend seeing the information in our stream documentation for other stream out details:
https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/32-stream-mode-t-series-datasheet/#section-header-two-ebb7e"
"""
