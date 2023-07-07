import time
from labjack import ljm
import socket
import pickle
import numpy as np
from datetime import date
import matplotlib.pyplot as plt
#import ljm_stream_util

# UPDATED: 03 July 2023
# NOTE: THIS IS A SIMPLER VERSION ONLY FOR RASTER TO TEST NEW METHOD (X IS SINE, Y IS STEP)
# TODO: check max frequency for sine values sent from buffer (given that we want to send out 256 values in half a period)
# TODO: Note: if max frequency allows it, our current upper limit for frequency is 500 Hz. (T/2 >= 1ms, T >= 2ms, 1/f >= 2/1000 s, 500 >= f)

# USER CAN CHANGE SCAN PARAMETERS IN CLASS BELOW!!
class raster:
    # sine_galvo = 'X',  step_galvo = 'Y'

    # USER CAN CHANGE SCAN PARAMETERS BELOW!!
    scan_name = 'digit_8' # 'three_lines'     # Info about image being scanned: {'digit', 'lines'}
    sine_freq = 10
    sine_voltage = 0.3      # amplitude, max value = 0.58  # galvo angle=voltage/0.22
    step_voltage = 0.3      # +- max and min voltages for stepping # galvo angle=voltage/0.22
    step_dim = 100          # step_dim = 1000/sine_freq  # todo???
    recordScan = True       # to connect to qutag

    # -----Extra params that can be changed for debugging--------
    pingQuTag = True
    diagnostics = False     # timeres file when False vs. txt file when True
    plotting = False
    currDate = date.today().strftime("%y%m%d")
    currTime = time.strftime("%Hh%Mm", time.localtime())
    filename = f'{scan_name}_sineAmp_({sine_voltage})_sineFreq({sine_freq})_stepDim(_{step_dim})_stepAmp_({step_voltage})_date({currDate})_time({currTime})'

# TODO: FILL IN NEW ADDRESSES
class T7:
    def __init__(self):
        self.handle = None  # Labjack device handle
        self.abort_scan = False  # Safety bool for parameter check
        # --------------- HARDCODED CLASS CONSTANTS BASED ON WIRING -------------
        # Servo and labjack addresses, note: we are using TickDAC
        self.x_address = "DAC1" # before: "TDAC1", now: "DAC1" to use buffer
        self.y_address = "TDAC0"  # --> in "FIO0"
        self.wait_address = "WAIT_US_BLOCKING"
        # QuTag addresses
        self.q_start_scan_addr = "FIO5"     # == 102?   # marks start of scan
        self.q_end_scan_addr = "FIO5"       # == 102?   # marks end of scan
        self.q_start_sweep_addr = ""    # == ?      # marks start of sine sweep row  # TODO!!!
        self.q_end_sweep_addr = ""      # == ?      # marks end of sine sweep row    # TODO!!!
        self.q_sweep_addr = "" # IF WE DON'T WANT ABOVE

        # Physical offset due to linearization of system (units: volts).
        self.x_offset = 0.59    # for "DAC1"
        self.y_offset = -0.289  # for "TDAC0"/"FIO0"

    # MAIN FUNCTION THAT PREPARES AND PERFORMS SCAN
    def main_galvo_scan(self):
        #print("\nStep 1) Defining scan parameters.")
        self.get_scan_parameters()
        #print("\nStep 2) Generating scan x,y values.")
        self.get_step_values()
        self.get_sine_values()
        print("\nStep 3) Doing safety check on scan parameters.")
        self.safety_check()
        if self.scanVariables.plotting:
            plot_values()
        if not self.abort_scan:
            print("\nStep 4) Opening labjack connection")
            self.open_labjack_connection()

            if self.recordScan:
                print("\nStep 5) Creating socket connection with Qutag server.")
                self.socket_connection()

            #print("\nStep 6) Populating command list.")
            self.populate_scan_lists()
            self.fill_buffer_stream()

            #print("\nStep 7) Setting start positions of galvos.")
            self.init_start_positions()
            time.sleep(1)

            print("\nStep 8) Performing scan...")
            self.start_scan()

    # Step 1) Sets all parameters depending on selected scan pattern and scan type
    # TODO: GO OVER AND DOUBLE CHECK (03/07-23)
    def get_scan_parameters(self):
        # --------------- HARDCODED FOR THIS SIMPLER METHOD ------------------------------
        self.sine_addr = self.x_address
        self.sine_offset = self.x_offset
        self.step_addr = self.y_address
        self.step_offset = self.y_offset
        # --------------- Chosen scan parameters ----------------------------------------
        self.scanVariables = raster()
        self.filename = self.scanVariables.filename
        self.recordScan = self.scanVariables.recordScan
        self.q_pingQuTag = self.scanVariables.pingQuTag
        self.diagnostics = self.scanVariables.diagnostics
        self.plotFigures = self.scanVariables.plotting  # bool if we want to plot theoretical
        # --------------- PLACEHOLDER VALUES --------------------------------------------
        # List of x and y values, and lists sent to Labjack:
        self.step_values = []       # values to step through
        self.step_times = []        # for plotting (single period)
        self.sine_values = []       # values for one sine period, for buffer
        self.sine_times = []        # for plotting (single period)
        self.aAddresses = []
        self.aValues = []
        # --------------- SINE ------------------------------
        self.b_max_buffer_size = 256  # Buffer stream size for y waveform values. --> Becomes resolution of sinewave period waveform == y_steps . i think it is max 512 samples (16-bit samples)?
        # Sine waveform:
        self.sine_amp = self.scanVariables.sine_voltage
        self.sine_freq = self.scanVariables.sine_freq
        self.sine_period = 1 / self.sine_freq
        self.sine_phase = np.pi / 2
        self.sine_dim =  self.b_max_buffer_size
        self.sine_delay = self.sine_period / self.sine_dim  # time between each y value in stream buffer     #self.sine_delay = 1 / (self.sine_dim / (2 * self.step_delay))
        # Buffer stream variables:
        self.b_samplesToWrite = self.sine_dim  # = how many values we save to buffer stream = y_steps = resolution of one period of sinewave, --> sent to TickDAC --> sent to y servo input
        self.b_scanRate = int( self.sine_dim / self.sine_period)  # scanrate = scans per second = samples per second for one address = (resolution for one sine period)/(one sine period)   NOTE: (2*self.step_delay) = self.sine_period (of sinewave)
        self.b_scansPerRead = self.b_scanRate  #int(self.b_scanRate / 2)  # NOTE: When performing stream OUT with no stream IN, ScansPerRead input parameter to LJM_eStreamStart is ignored. https://labjack.com/pages/support/?doc=%2Fsoftware-driver%2Fljm-users-guide%2Festreamstart
        self.b_targetAddress = ljm.nameToAddress(self.sine_addr)[0]
        self.b_streamOutIndex = 0  # index of: "STREAM_OUT0" I think this says which stream you want to get from (if you have several)
        self.b_aScanList = [ljm.nameToAddress("STREAM_OUT0")[0]]  # "STREAM_OUT0" == 4800
        self.b_nrAddresses = 1

        # --------------- STEP ------------------------------
        self.step_amp = self.scanVariables.step_voltage  # voltage = angle*0.22
        self.step_dim = self.scanVariables.step_dim
        self.step_delay = self.sine_period / 2  # time between every X command. Should be half a period (i.e. time for one up sweep)

        # Expected scan time:
        print("Sine -->  delay:", self.sine_delay, ", dim:", self.sine_dim, ", sine period:", self.sine_period)
        print("Step -->  delay:", self.step_delay, ", dim:", self.step_dim, ", sine period:", self.sine_period)
        self.scanTime = self.step_dim * self.step_delay * 1.5  # Note: it will be slightly higher than this which depends on how fast labjack can iterate between commands

    # Step 2) Returns a list of step values that the scan will perform
    def get_step_values(self):
        # TODO: CHECK THAT --> len(self.step_values) == self.step_dim
        # TODO: CHECK THAT CORRECT DELAY IS USED AND CORRECT VALUES GIVEN
        # populating "step_values" list with discrete values
        step_size = (2*self.step_amp) / (self.step_dim - 1)  # step size of our x values
        k = -self.step_amp
        for i in range(self.step_dim):
            self.step_times.append(i * self.step_delay)  # for plotting
            self.step_values.append(round(k + self.step_offset, 10))
            k += step_size

    # Step 2) Returns a list of sine values that the scan will perform
    def get_sine_values(self): # sine waveform
        # Change compared to before: now we don't ensure exactly symmetrical sine values for up/down sweeps.
        for i in range(self.sine_dim):
            t_curr = i * self.sine_delay
            val = self.sine_amp * np.sin((2 * np.pi * self.sine_freq * t_curr) - self.sine_phase)
            self.sine_times.append(t_curr)  # for plotting
            self.sine_values.append(round(val + self.sine_offset, 10))  # adding offset

    # Step 3) Error checks
    def safety_check(self):
        # TODO: CHECK THAT THIS STILL WORKS
        # MOST IMPORTANT SO WE DON'T DAMAGE DEVICE WITH TOO HIGH VOLTAGE:
        ErrorChecks().check_voltages()
        # Check to abort
        if self.abort_scan:
            print("Error check failed. Aborting scan.")
        else:
            print("\nError check succeeded. Continuing scan.")

    # Step 4) Connect to labjack device
    def open_labjack_connection(self):
        self.handle = ljm.openS("T7", "ANY", "ANY")  # ErrorCheck(self.handle, "LJM_Open")
        info = ljm.getHandleInfo(self.handle)  # ErrorCheck(info, "PrintDeviceInfoFromHandle")
        print(f"Opened a LabJack with Device type: {info[0]}, Connection type: {info[1]},\n "
              f"Serial number: {info[2]}, IP address: {ljm.numberToIP(info[3])}, Port: {info[4]},\n"
              f"Max bytes per MB: {info[5]} \n")

    # Step 5) Connect to qu_tag
    def socket_connection(self):
        # TODO: CLEAN UP LATER
        """ Sets up a server ot communciate to the qutag computer to start a measurement
            Sends the file and scan time to the computer"""
        HEADERSIZE = 10
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Establishes a server
        #host = socket.gethostname()
        host = '130.237.35.177'  # IP address of this computer
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
            # Mode is the qutag mode to produce a txt(0) or timeres file (1)
            if self.diagnostics:
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

    # Step 6) Adds x values and qtag pings and other commands to command list
    def populate_scan_lists(self):
        # Calculate residual delay
        wait_delay = 0.1 * 1000000  # wait_delay = self.step_delay * 1000000   # "Delays for x microseconds. Range is 0-100000
        remainingDelay = ((self.step_delay/0.1) - int(self.step_delay/0.1)) * 0.1 * 1000000
        print("Compare:", round(self.step_delay/0.1, 6), "?=", int(self.step_delay/0.1))
        print("total delay:", round(self.step_delay, 6))
        print("covered delay:", round(0.1*int(self.step_delay/0.1), 6))
        print("remaining delay=", round(self.step_delay - (0.1*int(self.step_delay/0.1)),6), "?=", remainingDelay)

        # Before scan: Add qtag start marker
        if self.q_pingQuTag:
            self.aAddresses += [self.q_start_scan_addr, self.wait_address, self.q_start_scan_addr]
            self.aValues += [1, 1, 0]

        # During scan:  # Add step values and pings to command list
        self.addScanMarkers_1_step(wait_delay, remainingDelay)        # TODO: ask if we want two repeating markers as we do at start and end of scan?

        # After: Send end marker to qtag
        if self.q_pingQuTag:
            self.aAddresses += [self.q_end_scan_addr, self.wait_address, self.q_end_scan_addr]
            self.aValues += [1, 1, 0]


    # CANDIDATE: PING ON OFF BEFORE AND AFTER WAITING
    def addScanMarkers_1_wait(self, wait_delay, remainingDelay):
        for step in self.step_values:
            # Add step value and "start marker"
            self.aAddresses += [self.step_addr]
            self.aValues += [step]

            self.aAddresses += [self.q_start_sweep_addr,  self.q_start_sweep_addr]
            self.aValues += [1, 0]

            self.addWaitDelay(wait_delay, remainingDelay)

            self.aAddresses += [self.q_end_sweep_addr, self.q_end_sweep_addr]
            self.aValues += [1, 0]

    # CANDIDATE: CANDIDATE LIKE WAIT ABOVE, WITH ADDED DELTA DELAY
    def addScanMarkers_2_wait(self, wait_delay, remainingDelay):
        delta = 1 # OR SOME DELAY

        for step in self.step_values:
            self.aAddresses += [self.step_addr]
            self.aValues += [step]

            self.aAddresses += [self.q_start_sweep_addr,  self.wait_address, self.q_start_sweep_addr]
            self.aValues += [1, delta, 0]

            self.addWaitDelay(wait_delay, remainingDelay)

            self.aAddresses += [self.q_end_sweep_addr,  self.wait_address, self.q_end_sweep_addr]
            self.aValues += [1, delta, 0]

    # CANDIDATE: PING ON OFF BEFORE AND AFTER STEPPING
    def addScanMarkers_1_step(self, wait_delay, remainingDelay):
        for step in self.step_values:
            # Add step value and "start marker"
            self.aAddresses += [self.q_start_sweep_addr, self.q_start_sweep_addr]
            self.aValues += [1, 0]

            self.aAddresses += [self.step_addr]
            self.aValues += [step]

            self.aAddresses += [self.q_end_sweep_addr, self.q_end_sweep_addr]  # note: not using end sweep address
            self.aValues += [1, 0]

            self.addWaitDelay(wait_delay, remainingDelay)

    # CANDIDATE: CANDIDATE LIKE STEP ABOVE, WITH ADDED DELTA DELAY
    def addScanMarkers_2_step(self, wait_delay, remainingDelay):
        delta = 1 # OR SOME DELAY   # Delay in microseconds. Range is 0-100000

        for step in self.step_values:
            # Add step value and "start marker"
            self.aAddresses += [self.q_start_sweep_addr,  self.wait_address, self.q_start_sweep_addr]
            self.aValues += [1, delta, 0]

            self.aAddresses += [self.step_addr]
            self.aValues += [step]

            self.aAddresses += [self.q_end_sweep_addr,  self.wait_address, self.q_end_sweep_addr]  # note: not using end sweep address
            self.aValues += [1, delta, 0]

            self.addWaitDelay(wait_delay, remainingDelay)

    # NOT LIKELY CANDIDATE: PING (to same address) ON BEFORE WAIT AND OFF AFTER WAIT
    def addScanMarkers_3_wait(self, wait_delay, remainingDelay):
        for step in self.step_values:
            # Add step value and "start marker"
            self.aAddresses += [self.step_addr]
            self.aValues += [step]

            self.aAddresses += [self.q_sweep_addr]
            self.aValues += [1]

            self.addWaitDelay(wait_delay, remainingDelay)

            self.aAddresses += [self.q_sweep_addr]  # note: not using end sweep address
            self.aValues += [0]
    # NOT LIKELY CANDIDATE: PING (to same address) ON BEFORE STEP AND OFF AFTER STEP
    def addScanMarkers_3_step(self, wait_delay, remainingDelay):
        for step in self.step_values:
            self.aAddresses += [self.q_sweep_addr]
            self.aValues += [1]

            self.aAddresses += [self.step_addr]
            self.aValues += [step]

            self.aAddresses += [self.q_sweep_addr]  # note: not using end sweep address
            self.aValues += [0]

            self.addWaitDelay(wait_delay, remainingDelay)

    def addWaitDelay(self, wait_delay, remainingDelay):
        # TODO: CHECK THAT RANGE INT ROUNDING DOESN'T MESS WITH TOTAL DELAY --> COUNT OR MAKE "int(self.step_delay / 0.1)" something we use to calculate the remaining delay
        # Add as many 0.1s delays as we can fit
        for i in range(int(self.step_delay / 0.1)):
            self.aAddresses += [self.wait_address]
            self.aValues += [wait_delay]
        # Add any residual delay
        if remainingDelay > 0:
            self.aAddresses += [self.wait_address]
            self.aValues += [remainingDelay]

    # Step 7) Write sine waveform values to stream buffer (memory)
    def fill_buffer_stream(self):
        # https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/32-stream-mode-t-series-datasheet/#section-header-two-ttmre
        try:
            print("Initializing stream out... \n")
            err = ljm.periodicStreamOut(self.handle, self.b_streamOutIndex, self.b_targetAddress, self.b_scanRate, self.b_samplesToWrite, self.sine_values)
            #print("Write to buffer error =", err)
        except ljm.LJMError:
            print("Failed upload buffer vals")
            #ljm_stream_util.prepareForExit(self.handle)
            self.close_labjack_connection()
            raise

    # Step 8) Sets sends positional commands to
    def init_start_positions(self):
        rc = ljm.eWriteNames(self.handle, 2, [self.step_addr, self.sine_addr], [self.step_values[0], self.sine_values[0]])
        print("Setting start positions for Step and Sine values:", self.step_values[0],", ",  self.sine_values[0])

    # Step 9) Actual scan is done here
    def start_scan(self):
        """ SCAN:
        --> Start buffer stream (y axis galvo will start moving now) and Send all scan commands to galvo/servo
        --> Send all stepping and ping values
        --> Stop Buffer
        --> Reset position to origo/offset
        """
        print(f"Expected scan time = {int(self.scanTime)} seconds")

        start_time = time.time()
        scanRate = ljm.eStreamStart(self.handle, self.b_scansPerRead, self.b_nrAddresses, self.b_aScanList, self.b_scanRate)
        rc = ljm.eWriteNames(self.handle, len(self.aAddresses), self.aAddresses, self.aValues)
        err = ljm.eStreamStop(self.handle)
        end_time = time.time()
        self.set_offset_pos()

        print("Actual scan time:", end_time - start_time)
        print("Scan Rate:", self.b_scanRate, "vs.", scanRate)
        print("Steam stop error (sine wave):", err)
        print("WriteNames error (stepping):", rc)

    # Sets galvos to set offset positions
    def set_offset_pos(self):
        rc = ljm.eWriteNames(self.handle, 2, [self.x_address, self.y_address], [self.x_offset, self.y_offset])

    # Terminates labjack connection
    def close_labjack_connection(self):
        print("Closing labjack connection...")
        if self.handle is None:
            print("\nT7 was not opened and therefore doesn't need closing")
        else:
            rc = ljm.eWriteNames(self.handle, 2, [self.x_address, self.y_address], [self.x_offset, self.y_offset])
            time.sleep(1)  # don't close too fast, just in case there is still something being transmitted
            err = ljm.close(self.handle)
            if err is None:
                print("Closing successful.")
            else:
                print("Problem closing T7 device. Error =", err)

# TODO: CHECK THAT ERROR CHECK STILL WORKS
class ErrorChecks:
    def check_voltages(self):
        # max is 5V but this gives a bit of margin, NOTE: val = 0.22*optical angle --> val = 1V is big enough for our scope
        max_voltage = 4

        # Checking that max allowed voltage is not changed. 5V is the absolute maximum allowed, but we give some margins
        if max_voltage > 4.5:
            print("Error: to high max voltage, change back to 4V or consult script author")
            t7.abort_scan = True

        for step in t7.step_values:
            # CHECKING INPUT VALUES TO SERVO, MAX ALLOWED IS 5V, WE HAVE 4V FOR MARGINS
            if abs(step) > max_voltage:
                print(f"Error: Too large voltage ({step}V) found in step list!")
                t7.abort_scan = True
        for val in t7.sine_values:
            # CHECKING INPUT VALUES TO SERVO, MAX ALLOWED IS 5V, WE HAVE 4V FOR MARGINS
            if abs(val) > max_voltage:
                print(f"Error: Too large voltage ({val}V) found in sine list!")
                t7.abort_scan = True
            # CHECKING INPUT VALUES TO SENT VIA TDAC, ONLY POSITIVE VALUES ALLOWED
            if val <= 0:
                print(f"Error: Negative voltage ({val}V) found in list for TDAC!")
                t7.abort_scan = True

def plot_values():
    plt.figure()
    plt.plot(t7.sine_values)
    plt.plot(t7.sine_values, 'r.', label="sine values (in buffer)")
    plt.plot(t7.step_values)
    plt.plot(t7.step_values, 'g.',  label="step values ")
    plt.legend()
    plt.xlabel("index")
    plt.ylabel("command voltage")
    plt.show()

# 1) Initiates labjack class
t7 = T7()
# 2) Prepare and perform scan
t7.main_galvo_scan()
# 3) Terminates labjack connection
t7.close_labjack_connection()