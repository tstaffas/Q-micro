import time
from labjack import ljm
import socket
import pickle
import numpy as np
from datetime import date
import matplotlib.pyplot as plt
#import sys  # unsure what we thought we needed this for


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
# TODO NOW:
#   > check and finish all buffer configs for burst stream
#   > implement two versions of "populate_scan_cmd_list_burst()"
#       ->  try both and choose!
#   > fix a nicer solution to "calc_wait_delays", with variables (maybe %)
#       -> calculate and check that it is correct! (maybe plot and sum up to a period?)
#       -> when complete, move out of function and directly into "get_scan_params()"
#       -> sub in the wait delay variables in function: "add_wait_delay()"
#           --> CHECK THAT RANGE INT ROUNDING DOESN'T MESS WITH TOTAL DELAY
#           --> COUNT OR MAKE "int(self.step_delay / 0.1)" something we use to calculate the remaining delay
#   > check function "get_step_values()":
#       -> len(self.step_values) == self.step_dim
#       -> CORRECT DELAY IS USED AND CORRECT VALUES GIVEN  (plotting?)
#   > Go through entire logic and make sure no bad values can be sent to servo amps
#   > !! ANSWER CAROLS EMAIL FOR FKS SAKE !!
# ------------------------------------------------------------

# UPDATED 17 JULY 2023

class Raster:  # USER CAN CHANGE SCAN CLASS PARAMETERS BELOW!!

    scan_name = 'multitrigger_digit_8_single_marker'     # Info about image being scanned: {'digit', 'lines'}
    sine_freq = 1
    sine_voltage = 0.3      # amplitude, max value = 0.58  -->  galvo angle=voltage/0.22
    step_voltage = 0.3      # +- max and min voltages for stepping  -->   galvo angle=voltage/0.22
    step_dim = 10          # TODO check if there is a limit here???  step_dim = 1000/sine_freq ???

    recordScan = False       # to connect to qutag to record data
    ping101 = True           # marker BEFORE step, after sweep ends
    ping102 = False            # marker AFTER step, before sweep starts

    # -----Extra params that shouldn't change but can be for debugging--------
    pingQuTag = True
    useTrigger = True
    diagnostics = False     # timeres file when False vs. txt file when True
    currDate = date.today().strftime("%y%m%d")
    currTime = time.strftime("%Hh%Mm%Ss", time.localtime())
    filename = f'{scan_name}_sineFreq({sine_freq})_sineAmp({sine_voltage})_stepAmp({step_voltage})_stepDim({step_dim})_date({currDate})_time({currTime})'


class T7:
    def __init__(self):
        self.handle = None          # Labjack device handle
        self.abort_scan = False     # Important safety bool for parameter checks
        # --------------- HARDCODED CLASS CONSTANTS BASED ON WIRING -------------
        
        self.wait_address = "WAIT_US_BLOCKING"
        self.x_address = "DAC1"         # Values sent from periodic buffer (which is not compatable with TDAC)
        self.y_address = "TDAC2"        # TickDAC via LJ port "FIO2" (TDAC IN PORTS FIO2 FIO3)

        self.q_M101_addr = "FIO7"       # marker channel = 101, LJ port FIO5
        self.q_M102_addr = "FIO4"       # marker channel = 102, LJ port FIO2
        # IMPORTANT! IF WE USE MARKERS 103 OR 100, ADD THEM TO check_cmd_list() FUNCTION!
        #self.q_M103_addr = "FIO5"     # marker channel = 100, LJ port FIO3
        #self.q_M100_addr = "FIO6"     # marker channel = 103, LJ port FIO4

        # TRIGGERED STREAM, USING FIO0 and FIO1:
        self.tr_source_addr = "FIO0"    # Address for channel that outputs the trigger pulse
        self.tr_sink_addr = "DIO1"      # Address for channel that gets trigger pulse, and trigger stream on/off when pulse is recieved
    
        # Physical offset due to linearization of system (units: volts)
        self.x_offset = 0.59
        self.y_offset = -0.289

    # MAIN FUNCTION THAT PREPARES AND PERFORMS SCAN:
    def main_galvo_scan(self):
        #print("\nStep 1) Defining scan parameters.") 
        self.get_scan_parameters()

        #print("\nStep 2) Generating scan x,y values.")
        self.get_step_values()
        self.get_sine_values()

        #print("\nStep 3) Doing safety check on scan parameters.")
        SafetyTests().check_voltages()  # MOST IMPORTANT SO WE DON'T DAMAGE DEVICE WITH TOO HIGH VOLTAGE

        if not self.abort_scan:

            #print("\nStep 4) Opening labjack connection")
            self.open_labjack_connection()
            #err = ljm.eStreamStop(self.handle)

            #print("\nStep 6) Populating command list.")
            self.populate_scan_cmd_list_burst()
            #self.populate_buffer_stream()
            self.fill_buffer_stream()

            # Double check that scan command lists are safe
            SafetyTests().check_cmd_list()
            if self.abort_scan:
                return

            if self.useTrigger:  # alternative is that we use "STREAM_ENABLE" as a sort of trigger
                #print("Prepping stream trigger")
                self.configure_stream_trigger()

            # Finish stream configs , replaces: ljm.eStreamStart(self.handle, self.b_scansPerRead, self.b_nrAddresses, self.b_aScanList, self.b_scanRate)
            self.configure_stream_start()

            if self.recordScan:
                print("\nStep 5) Creating socket connection with Qutag server.")
                self.socket_connection()

            #print("\nStep 8) Performing scan...")
            self.start_scan()

    # Step 1) Sets all parameters depending on selected scan pattern and scan type
    def get_scan_parameters(self):
        # --------------- HARDCODED FOR THIS SIMPLER METHOD ------------------------------
        self.sine_addr = self.x_address
        self.sine_offset = self.x_offset
        self.step_addr = self.y_address
        self.step_offset = self.y_offset
        # --------------- Chosen scan parameters ----------------------------------------
        self.scanVariables = Raster()
        self.filename = self.scanVariables.filename
        self.recordScan = self.scanVariables.recordScan
        self.q_pingQuTag = self.scanVariables.pingQuTag
        self.diagnostics = self.scanVariables.diagnostics
        self.useTrigger = self.scanVariables.useTrigger
        self.ping101 = self.scanVariables.ping101  # marker before step
        self.ping102 = self.scanVariables.ping102  # marker after step
        # --------------- PLACEHOLDER VALUES --------------------------------------------
        # List of x and y values, and lists sent to Labjack:
        self.step_values = []       # values to step through
        self.step_times = []        # for plotting (single period)
        self.sine_values = []       # values for one sine period, for buffer
        self.sine_times = []        # for plotting (single period)
        self.aAddresses = []
        self.aValues = []
        # --------------- SINE ------------------------------ 
        self.b_max_buffer_size = 512  # Buffer stream size for y waveform values. --> Becomes resolution of sinewave period waveform == y_steps . i think it is max 512 samples (16-bit samples)?
        # Sine waveform: 
        self.sine_amp = self.scanVariables.sine_voltage
        self.sine_freq = self.scanVariables.sine_freq
        self.sine_period = 1 / self.sine_freq
        self.sine_phase = np.pi / 2
        self.sine_dim = int(self.b_max_buffer_size/2)  # sine_dim = samplesToWrite = how many values we save to buffer stream = y_steps = resolution of one period of sinewave, --> sent to TickDAC --> sent to y servo input
        self.sine_delay = self.sine_period / self.sine_dim  # time between each y value in stream buffer     #self.sine_delay = 1 / (self.sine_dim / (2 * self.step_delay))
        # Buffer stream variables: 
        self.b_scanRate = int(self.sine_dim / self.sine_period)  # scanrate = scans per second = samples per second for one address = (resolution for one sine period)/(one sine period)   NOTE: (2*self.step_delay) = self.sine_period (of sinewave)
        # TODO: what happens if we set "b_scansPerRead" to 0 instead? 
        self.b_scansPerRead = self.b_scanRate  #int(self.b_scanRate / 2)  # NOTE: When performing stream OUT with no stream IN, ScansPerRead input parameter to LJM_eStreamStart is ignored. https://labjack.com/pages/support/?doc=%2Fsoftware-driver%2Fljm-users-guide%2Festreamstart
        self.b_targetAddress = ljm.nameToAddress(self.sine_addr)[0]
        self.b_streamOutIndex = 0  # index of: "STREAM_OUT0" I think this says which stream you want to get from (if you have several)
        self.b_aScanList = [ljm.nameToAddress("STREAM_OUT0")[0]]  # "STREAM_OUT0" == 4800  
        self.b_nrAddresses = 1

        # --------------- STEP ------------------------------
        self.step_amp = self.scanVariables.step_voltage  # voltage = angle*0.22
        self.step_dim = self.scanVariables.step_dim

        # -----------------------
        self.extra_delay = 0.15  # extra delay (seconds) to ensure that sine curve has reached a minimum
        self.step_delay = self.sine_period + self.extra_delay  # time between every X command. Should be half a period (i.e. time for one up sweep)

        # calculates constants we need to do wait_us_blocking for any frequency. NOTE!!! Can be moved to get_params func
        # Calculate residual delay for step delay (a full period)
        self.wait_delay = 0.1 * 1000000  # wait_delay = self.step_delay * 1000000   # "Delays for x microseconds. Range is 0-100000
        coveredDelay = 0.1*int(self.step_delay/0.1)
        self.remaining_delay = (round(self.step_delay/0.1, 10) - int(self.step_delay / 0.1)) * 0.1 * 1000000
        print("total delay:", round(self.step_delay, 6))
        print("covered delay:", round(coveredDelay, 6), "seconds")
        print("remaining delay:", round(self.step_delay - coveredDelay, 6), "?=", self.remaining_delay/1000000)
        # -----------------------
        # Expected scan time:
        self.scanTime = self.step_dim * self.step_delay * 1.5  # Note: it will be slightly higher than this which depends on how fast labjack can iterate between commands

    # Step 2) Returns a list of step and sine values that the scan will perform
    def get_step_values(self):
        # populating "step_values" list with discrete values
        step_size = (2*self.step_amp) / (self.step_dim - 1)  # step size of our x values
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
        #print(f"Opened a LabJack with Device type: {info[0]}, Connection type: {info[1]},\n "
              #f"Serial number: {info[2]}, IP address: {ljm.numberToIP(info[3])}, Port: {info[4]},\n"
              #f"Max bytes per MB: {info[5]} \n")
 
    # Step 5) Connect to qu_tag 
    def socket_connection(self):
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
    def populate_scan_cmd_list_burst(self):  # USE TRIGGER WE HAVE SET UP PREVIOUSLY
        #print("OPTION 1: external trigger")
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

        self.cmd_pulse_trigger(state="arm")
        for step in self.step_values:
            # self.cmd_marker(102)

            #for i in range(10):
            #    self.aAddresses += [self.wait_address]# TEMP REMOVE
            #    self.aValues += [self.wait_delay]     # TEMP REMOVE

            self.cmd_step_value(step)

            #for i in range(10):
            #    self.aAddresses += [self.wait_address]# TEMP REMOVE
            #    self.aValues += [self.wait_delay]     # TEMP REMOVE

            self.cmd_marker(101)

            self.cmd_pulse_trigger(state="fire")

            self.add_wait_delay()   # waits a period and a delta extra

            # do below instead of add_wait_delay to see that we do need to wait a full period
            #self.aAddresses += [self.wait_address]
            #self.aValues += [self.wait_delay]

             # RESETTING TRIGGER ETC:
            self.cmd_enable_trigger("off")
            self.cmd_pulse_trigger(state="arm")
            self.reset_num_scans()  # NEED TO RESET STUFF
            self.cmd_enable_trigger("on")

    def reset_num_scans(self):
        self.aAddresses += ["STREAM_NUM_SCANS"]
        self.aValues += [self.sine_dim]

    def add_wait_delay(self ):
        # Add as many 0.1s delays as we can fit
        for i in range(int(self.step_delay / 0.1)):
            self.aAddresses += [self.wait_address]
            self.aValues += [self.wait_delay]
        # Add any residual delay
        if self.remaining_delay > 0:
            self.aAddresses += [self.wait_address]
            self.aValues += [self.remaining_delay]

    # marker = {101, 102}
    def cmd_marker(self, marker):
        # Add "step marker"
        if self.q_pingQuTag:
            if marker == 101 and self.ping101:
                self.aAddresses += [self.q_M101_addr, self.q_M101_addr]
                self.aValues += [1, 0]

            elif marker == 102 and self.ping102:
                self.aAddresses += [self.q_M102_addr, self.q_M102_addr]  # note: not using end sweep address
                self.aValues += [1, 0]
            else:
                pass

    # pulse state = {"arm", "fire"}
    def cmd_pulse_trigger(self, state):
        if self.useTrigger:
            # Send a falling edge to the source of the trigger pulse, which is connected to the trigger channel --> Triggers stream.
            if state == "arm":
                self.aAddresses += [self.tr_source_addr]
                self.aValues += [1]     # arm/setup trigger --> 1=High
            elif state == "fire":  # trigger is set off by falling edge (edge from 1 to 0)
                self.aAddresses += [self.tr_source_addr]
                self.aValues += [0]     # execute trigger --> 0=Low
        else:
            print("Error. Incorrect trigger based on 'useTrigger' parameter.")

    # enable state = {"on", "off"}
    def cmd_enable_trigger(self, state):
        # instead of jumper trigger, use "ENABLE_STREAM"
        if self.useTrigger:   #        if not self.useTrigger: before
            if state == "on":
                self.aAddresses += ["STREAM_ENABLE"]  # TODO CHECK SYNTAX FOR ADDRESS
                self.aValues += [1]  # 1=High

            elif state == "off":
                self.aAddresses += ["STREAM_ENABLE"]  # TODO CHECK SYNTAX FOR ADDRESS
                self.aValues += [0]  # 0=Low
            else:
                print("Error in enable stream")
                self.abort_scan = True
        else:
            print("Error. Incorrect enable trigger based on 'useTrigger' parameter.")

    def cmd_step_value(self, step):
        # Add step value
        self.aAddresses += [self.step_addr]
        self.aValues += [step]

    # Step 7) Write sine waveform values to stream buffer (memory)
    def fill_buffer_stream(self):
        # https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/32-stream-mode-t-series-datasheet/#section-header-two-ttmre
        try:
            # print("Initializing stream out... \n")
            err = ljm.periodicStreamOut(self.handle, self.b_streamOutIndex, self.b_targetAddress, self.b_scanRate, self.sine_dim, self.sine_values)
            # print("Write to buffer error =", err)
        except ljm.LJMError:
            print("Failed upload buffer vals")
            # ljm_stream_util.prepareForExit(self.handle)
            self.close_labjack_connection()
            raise

    # Step 7) Write sine waveform values to stream buffer (memory)
    def OLD_populate_buffer_stream(self):
        # https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/32-stream-mode-t-series-datasheet/#section-header-two-ttmre
        # previously had: ljm.periodicStreamOut(self.handle, self.b_streamOutIndex, self.b_targetAddress, self.b_scanRate, self.sine_dim, self.sine_values)
        try:
            #self.b_streamOutIndex                      done, don't need
            #self.b_targetAddress                       done
            #self.b_scanRate                            # TODO: this should be defined somewhere here, i think
            #self.b_samplesToWrite or self.sine_dim     # TODO check, i think this is used to decide if we do F32 or U16 --> maybe don't need
            #self.sine_values                           done

            # TODO: CHECK IF WE NEED TO TURN OFF "STREAM_ENABLE" BELOW BEFORE STARTING
            #ljm.eWriteName(self.handle, "STREAM_ENABLE", 0)                                                 # ?? start by turning off any stream in case it's on?
            #ljm.eWriteName(self.handle, "STREAM_BUFFER_SIZE_BYTES", self.b_max_buffer_size)    # allows for 256 float (F32) values (max limit for DAC)

            ljm.eWriteName(self.handle, "STREAM_OUT0_ENABLE", 0)                                            # disable stream 0 while configuring
            ljm.eWriteName(self.handle, "STREAM_OUT0_TARGET", self.b_targetAddress)                         # physical I/O that outputs buffer values
            ljm.eWriteName(self.handle, "STREAM_OUT0_BUFFER_ALLOCATE_NUM_BYTES", self.b_max_buffer_size)    # allows for 256 float (F32) values (max limit for DAC)
            ljm.eWriteName(self.handle, "STREAM_OUT0_ENABLE", 1)
            # enable stream 0 when done configuring
            # list of values to write to buffer, should be 256 values for full period
            ljm.eWriteNameArray(self.handle, "STREAM_OUT0_BUFFER_F32", self.sine_dim, self.sine_values)
            ljm.eWriteName(self.handle, "STREAM_OUT0_LOOP_NUM_VALUES", 1)
            ljm.eWriteName(self.handle, "STREAM_OUT0_SET_LOOP", 1)

        except ljm.LJMError:
            print("Failed upload buffer vals")
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
            ljm.eWriteName(self.handle, "STREAM_NUM_SCANS", self.sine_dim)  # = 256, how many values in buffer we want to burst stream (full period of values)
            ljm.eWriteName(self.handle, "STREAM_SCANRATE_HZ", self.b_scanRate)  #
            ljm.eWriteName(self.handle, "STREAM_NUM_ADDRESSES", self.b_nrAddresses)  # len(b_aScanList), nr of output channels/streams
            #ljm.eWriteName(self.handle, "STREAM_AUTO_TARGET", )  # TODO CHECK IF NEEDED
            ljm.eWriteName(self.handle, "STREAM_SCANLIST_ADDRESS0", self.b_aScanList[0])  # TODO CHECK IF NEEDED AND WHAT IT IS
            #ljm.eWriteName(self.handle, "STREAM_DATATYPE", 0)  # ???? TODO CHECK IF NEEDED
            if self.useTrigger:
                ljm.eWriteName(self.handle, "STREAM_ENABLE", 1)  # ???? TODO CHECK IF NEEDED
            # TODO: READ BACK ACTUAL SCAN RATE SOMEHOW
            # print("Scan Rate:", self.b_scanRate, "vs.", scanRate)
        except ljm.LJMError:
            print("Failed config buffer stream")
            self.close_labjack_connection()
            raise

    # Set up trigger for buffer stream:
    def configure_stream_trigger(self):
        # https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/132-dio-extended-features-t-series-datasheet/
        #print("Configuring trigger")

        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0) # disabling triggered stream, also clears previous settings i think
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
        ljm.eWriteName(self.handle, "%s_EF_CONFIG_A" % self.tr_sink_addr, 0)  # 0: Falling edges , 1: Rising edges (<-i think, depends on bitmask)
        # Turn on the DIO-EF  --> Enable trigger once configs are done
        ljm.eWriteName(self.handle, "%s_EF_ENABLE" % self.tr_sink_addr, 1)

        # Arming/loading trigger. Trigger activates when self.tr_source_addr goes from 1 to 0 --> falling edge trigger
        #ljm.eWriteName(self.handle, self.tr_source_addr, 1)

    # Step 8) Sets start scan positions of galvos
    def init_start_positions(self):
        if abs(self.step_values[0]) < 5 and abs(self.sine_values[0]) < 5:
            ljm.eWriteNames(self.handle, 2, [self.step_addr, self.sine_addr], [self.step_values[0], self.sine_values[0]])
            #print("Setting start positions for Step and Sine values:", self.step_values[0],", ",  self.sine_values[0])
        else:
            self.abort_scan = True

    def test_trigger(self):
        if self.useTrigger:
            print("")
            print("-------")
            print(f"Stream activated, but waiting. ")
            print(f"You can trigger stream now via a falling edge on {self.tr_source_addr}.\n")
            print("Sleeping 3 seconds to test trigger:")
            for i in range(1, 3):
                print(i, "s ...")
                time.sleep(1)

    # Step 9) Actual scan is done here
    def start_scan(self):
        try:
            if self.abort_scan:  # last line of defense
                return

            # print("\nSetting start positions of galvos.")
            self.init_start_positions()
            time.sleep(1)  # give galvo a bit of time to reach start pos

            # waits 5 seconds after trigger is set up, can be removed later
            #self.test_trigger()

            print("Calling ljm.WriteNames(...)")

            start_time = time.time()
            rc = ljm.eWriteNames(self.handle, len(self.aAddresses), self.aAddresses, self.aValues)
            end_time = time.time()

            err = ljm.eStreamStop(self.handle)
            print(f"\nTheoretical scan time = {self.step_dim * self.step_delay} seconds")
            print(f"Actual scan time   = {round(end_time - start_time, 6)} seconds\n")

            # reset galvo positions to offset:
            self.set_offset_pos()

        except ljm.LJMError:
            print("Failed scan")
            #err = ljm.eStreamStop(self.handle)
            self.close_labjack_connection()
            raise

    # Sets galvos to set offset positions 
    def set_offset_pos(self):
        ljm.eWriteNames(self.handle, 2, [self.x_address, self.y_address], [self.x_offset, self.y_offset])

    # Terminates labjack connection 
    def close_labjack_connection(self):
        print("Closing labjack connection...")
        if self.handle is None:
            print("\nT7 was not opened and therefore doesn't need closing")
        else:
            # reset galvo positions to offset:
            self.set_offset_pos()

            # clear trigger source voltage:
            ljm.eWriteName(self.handle, self.tr_source_addr, 0)  # send 0 just in case to stop any input

            # wait and close connection
            time.sleep(1)                   # probably don't need, just in case there is still some data being transmitted
            err = ljm.close(self.handle)

            if err is None:
                print("Closing successful.")
            else:
                print("Problem closing T7 device. Error =", err)


class SafetyTests:
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
            # CHECKING INPUT VALUES TO SENT VIA DAC, ONLY POSITIVE VALUES ALLOWED
            if val <= 0:
                print(f"Error: Negative voltage ({val}V) found in list for DAC!")
                t7.abort_scan = True

    def check_cmd_list(self):
        if len(t7.aAddresses) != len(t7.aValues):
            print("ERROR. NOT SAME COMMAND LIST LENGTHS. MISALIGNMENT DANGER.")
            t7.abort_scan = True

        for i in range(len(t7.aAddresses)):
            if t7.aAddresses[i] == t7.tr_source_addr:
                if t7.aValues[i] != 0 and t7.aValues[i] != 1:
                    print("ERROR. INVALID VALUE FOR EDGE SOURCE VALUE")
                    t7.abort_scan = True

            elif t7.aAddresses[i] == t7.tr_sink_addr:
                print("ERROR. SINK SHOULD NOT BE A COMMAND TARGET ADDRESS")
                t7.abort_scan = True

            elif t7.aAddresses[i] == t7.wait_address:
                if t7.aValues[i] < 100 and t7.aValues[i] != 0:
                    print("ERROR. ", t7.aValues[i], " WAIT VALUE IS TOO SMALL.")
                    t7.abort_scan = True

            elif t7.aAddresses[i] == t7.step_addr:
                if abs(t7.aValues[i]) > 4:
                    print("ERROR. VALUE TOO BIG")
                    t7.abort_scan = True

            elif t7.aAddresses[i] == t7.sine_addr:
                print("ERROR. SINE VALUE IN COMMAND LIST")
                t7.abort_scan = True
                if abs(t7.aValues[i]) > 4:
                    print("ERROR. VALUE TOO BIG")

            elif (t7.aAddresses[i] == t7.q_M101_addr) or (t7.aAddresses[i] == t7.q_M102_addr):
                if t7.aValues[i] != 0 and t7.aValues[i] != 1:
                    print("ERROR. MARKER VALUE ERROR. MUST BE IN {0,1}")
                    t7.abort_scan = True

            elif t7.aAddresses[i] == "STREAM_ENABLE" or t7.aAddresses[i] == "STREAM_NUM_SCANS":
                pass
            else:
                print(t7.aAddresses[i], "... Address not recognized or checked for in 'check_cmd_list()'. Aborting scan.")

                t7.abort_scan = True

        if t7.abort_scan:
            print("\nFinal Check Failed...\n")
        else:
            print("\nFinal Check Succeeded!\n")


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
