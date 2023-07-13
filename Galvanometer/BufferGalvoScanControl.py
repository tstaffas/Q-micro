import time
from labjack import ljm
import socket
import pickle
import numpy as np
from datetime import date
import matplotlib.pyplot as plt
#import ljm_stream_util
import sys  # ??


# UPDATED 07 JULY 2023

# TODO: check max frequency for sine values sent from buffer (given that we want to send out 256 values in half a period)
# TODO: Note: if max frequency allows it, our current upper limit for frequency is 500 Hz. (T/2 >= 1ms, T >= 2ms, 1/f >= 2/1000 s, 500 >= f)

# USER CAN CHANGE SCAN PARAMETERS IN CLASS BELOW!!

class raster:
    # sine_galvo = 'X',  step_galvo = 'Y'

    # USER CAN CHANGE SCAN PARAMETERS BELOW!!
    scan_name = 'digit_8_double_markers'     # Info about image being scanned: {'digit', 'lines'}
    sine_freq = 10
    sine_voltage = 0.3      # amplitude, max value = 0.58  # galvo angle=voltage/0.22
    step_voltage = 0.3      # +- max and min voltages for stepping # galvo angle=voltage/0.22
    step_dim = 100          # step_dim = 1000/sine_freq  # todo???
    recordScan = True       # to connect to qutag
    ping1 = True    # marker before step
    ping2 = True    # marker after step
    # -----Extra params that can be changed for debugging--------
    pingQuTag = True
    useTrigger = True

    diagnostics = False     # timeres file when False vs. txt file when True
    plotting = False
    currDate = date.today().strftime("%y%m%d")
    currTime = time.strftime("%Hh%Mm%Ss", time.localtime())
    filename = f'{scan_name}_sineAmp_({sine_voltage})_sineFreq({sine_freq})_stepDim(_{step_dim})_stepAmp_({step_voltage})_date({currDate})_time({currTime})'


class T7:
    def __init__(self):
        self.handle = None  # Labjack device handle
        self.abort_scan = False  # Safety bool for parameter check
        # --------------- HARDCODED CLASS CONSTANTS BASED ON WIRING -------------
        
        # LabJack addresses, note: we are using TickDAC for one axis
        self.wait_address = "WAIT_US_BLOCKING"
        self.x_address = "DAC1"       # Values sent from periodic buffer (which is not compatable with TDAC)
        self.y_address = "TDAC2" # MOVED TDAC TO PORTS FIO2 FIO3 TO TEST TRIGGER      #"TDAC0"      # TDAC via LJ port "FIO0"
        # QuTag addresses: DISABLED UNTIL THEO MOVES MARKERS
        self.q_M102_addr = "FIO4"     # marker channel = 102, LJ port FIO2
        #self.q_M103_addr = "FIO5"     # marker channel = 100, LJ port FIO3
        #self.q_M100_addr = "FIO6"     # marker channel = 103, LJ port FIO4
        self.q_M101_addr = "FIO7"     # marker channel = 101, LJ port FIO5
        
        # Buffer stream addresses
        # https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/32-stream-mode-t-series-datasheet/#section-header-two-kmwnd

        # MOVED TDAC AND USING FIO0 and FIO1 for TRIGGER STREAM
        self.tr_source_addr = "FIO0"   # Address for channel that outputs the trigger pulse
        self.tr_sink_addr = "DIO1"     # Address for channel that gets trigger pulse, and trigger stream on/off when pulse is recieved
    
        # Physical offset due to linearization of system (units: volts).
        self.x_offset = 0.59    # for "DAC1"
        self.y_offset = -0.289  # for "TDAC0"

    # MAIN FUNCTION THAT PREPARES AND PERFORMS SCAN
    def main_galvo_scan(self):
        #print("\nStep 1) Defining scan parameters.") 
        self.get_scan_parameters()
        #print("\nStep 2) Generating scan x,y values.")
        self.get_step_values()
        self.get_sine_values()
        #print("\nStep 3) Doing safety check on scan parameters.")
        self.safety_check()
        if self.scanVariables.plotting:
            plot_values()
        if not self.abort_scan:
            #print("\nStep 4) Opening labjack connection")
            self.open_labjack_connection()

            if self.recordScan:
                print("\nStep 5) Creating socket connection with Qutag server.")
                self.socket_connection()

            #print("\nStep 6) Populating command list.")
            self.populate_scan_lists()
            self.fill_buffer_stream()
            
            #print("\nStep 7) Setting start positions of galvos.") 
            self.init_start_positions()
            time.sleep(1)  # give galvo a bit of time to reach start pos

            if self.useTrigger:
                ljm.eWriteName(self.handle, self.tr_source_addr, 0)  # make sure source starts on 0V
                #print("Prepping stream trigger")
                self.configure_stream_trigger()

            #print("\nStep 8) Performing scan...")
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
        self.useTrigger = self.scanVariables.useTrigger
        self.ping1 = self.scanVariables.ping1  # marker before step
        self.ping2 =  self.scanVariables.ping2  # marker after step
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
        self.sine_dim =  self.b_max_buffer_size   # max at 512 right now but has worked with half that
        self.sine_delay = self.sine_period / self.sine_dim  # time between each y value in stream buffer     #self.sine_delay = 1 / (self.sine_dim / (2 * self.step_delay))
        # Buffer stream variables: 
        self.b_samplesToWrite = self.sine_dim  # = how many values we save to buffer stream = y_steps = resolution of one period of sinewave, --> sent to TickDAC --> sent to y servo input
        self.b_scanRate = int( self.sine_dim / self.sine_period)  # scanrate = scans per second = samples per second for one address = (resolution for one sine period)/(one sine period)   NOTE: (2*self.step_delay) = self.sine_period (of sinewave)
        # TODO: what happens if we set "b_scansPerRead" to 0 instead? 
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
        #print("Sine -->  delay:", self.sine_delay, ", dim:", self.sine_dim, ", sine period:", self.sine_period)
        #print("Step -->  delay:", self.step_delay, ", dim:", self.step_dim, ", sine period:", self.sine_period)
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
    def get_sine_values(self):  # sine waveform 
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
            pass
            #print("\nError check succeeded. Continuing scan.")

    # Step 4) Connect to labjack device
    def open_labjack_connection(self):
        self.handle = ljm.openS("T7", "ANY", "ANY")  # ErrorCheck(self.handle, "LJM_Open")
        info = ljm.getHandleInfo(self.handle)  # ErrorCheck(info, "PrintDeviceInfoFromHandle")
        #print(f"Opened a LabJack with Device type: {info[0]}, Connection type: {info[1]},\n "
              #f"Serial number: {info[2]}, IP address: {ljm.numberToIP(info[3])}, Port: {info[4]},\n"
              #f"Max bytes per MB: {info[5]} \n")
 
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

    # for testing that mirror can move one sine period via writenames() for troubleshooting
    def debug_populate_sine_scan_lists(self):
        for si in self.sine_values:
            self.aAddresses += [self.sine_addr]
            self.aValues += [si]
            self.aAddresses += [self.wait_address]
            self.aValues += [self.sine_delay*1000000]


    # Step 6) Adds x values and qtag pings and other commands to command list
    # TODO: make sure that "self.tr_source_addr" starts with 0V before we set up the trigger
    # TODO: Check that the trigger is set to the falling edge, or coordinate a correct pulse/edge
    def populate_scan_lists(self):
        # Calculate residual delay
        self.wait_delay = 0.1 * 1000000  # wait_delay = self.step_delay * 1000000   # "Delays for x microseconds. Range is 0-100000
        self.remaining_delay = ((self.step_delay/0.1) - int(self.step_delay/0.1)) * 0.1 * 1000000
        #print("Compare:", round(self.step_delay/0.1, 6), "?=", int(self.step_delay/0.1))
        #print("total delay:", round(self.step_delay, 6))
        #print("covered delay:", round(0.1*int(self.step_delay/0.1), 6))
        #print("remaining delay=", round(self.step_delay - (0.1*int(self.step_delay/0.1)),6), "?=", self.remaining_delay)

        # Send an edge to the source of the trigger pulse. The source is connected to the trigger channel. the Triggers the stream buffer.
        #Note that before low is set below and before stream is started, we set high on source to "arm" the trigger
        if self.useTrigger:
            self.aAddresses += [self.tr_source_addr]
            self.aValues += [0]   # 1=High, 0=Low

        for step in self.step_values:
            # Add "step marker"
            if self.q_pingQuTag and self.ping1:
                self.aAddresses += [self.q_M101_addr, self.q_M101_addr]
                self.aValues += [1, 0]

            # Add step value
            self.aAddresses += [self.step_addr]
            self.aValues += [step]

            if self.q_pingQuTag and self.ping2:
                # Add "step marker"
                self.aAddresses += [self.q_M102_addr, self.q_M102_addr]  # note: not using end sweep address
                self.aValues += [1, 0]

            # Add wait delay for half a period
            self.addWaitDelay()

    def addWaitDelay(self):
        # TODO: CHECK THAT RANGE INT ROUNDING DOESN'T MESS WITH TOTAL DELAY --> COUNT OR MAKE "int(self.step_delay / 0.1)" something we use to calculate the remaining delay
        # Add as many 0.1s delays as we can fit
        for i in range(int(self.step_delay / 0.1)):
            self.aAddresses += [self.wait_address]
            self.aValues += [self.wait_delay]
        # Add any residual delay
        if self.remaining_delay > 0:
            self.aAddresses += [self.wait_address]
            self.aValues += [self.remaining_delay]

    # Step 7) Write sine waveform values to stream buffer (memory)  
    def fill_buffer_stream(self):
        # https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/32-stream-mode-t-series-datasheet/#section-header-two-ttmre
        try:
            #print("Initializing stream out... \n")
            err = ljm.periodicStreamOut(self.handle, self.b_streamOutIndex, self.b_targetAddress, self.b_scanRate, self.b_samplesToWrite, self.sine_values)
            #print("Write to buffer error =", err)
        except ljm.LJMError:
            print("Failed upload buffer vals")
            #ljm_stream_util.prepareForExit(self.handle)
            self.close_labjack_connection()
            raise

    # TODO: make sure constants are imported
    def configure_stream_trigger(self):
        print("Configuring trigger")
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0) # disabling triggered stream
        ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)  # Enabling internally-clocked stream.
        ljm.eWriteName(self.handle, "STREAM_RESOLUTION_INDEX", 0)
        ljm.eWriteName(self.handle, "STREAM_SETTLING_US", 0)
        ljm.eWriteName(self.handle, "AIN_ALL_RANGE", 0)
        ljm.eWriteName(self.handle, "AIN_ALL_NEGATIVE_CH", ljm.constants.GND)
        # ----
        # Configure LJM for unpredictable stream timing. By default, LJM will time out with an error while waiting for the stream trigger to occur.       
        # note: in the C++ code this part comes here, but in the python version it comes just before streamstart
        ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, ljm.constants.STREAM_SCANS_RETURN_ALL_OR_NONE)
        ljm.writeLibraryConfigS(ljm.constants.STREAM_RECEIVE_TIMEOUT_MS, 0)
        # ----
        # https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/132-dio-extended-features-t-series-datasheet/
        # Define which address trigger is. Example:  2000 sets DIO0 / FIO0 as the stream trigger
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", ljm.nameToAddress(self.tr_sink_addr)[0])
        self.DIO_EF_12_setup()  # CONDITIONAL RESET

    # CONFIGS FOR EF INDEX 12: CONDITIONAL RESET
    def DIO_EF_12_setup(self):
        # Clear any previous settings on triggerName's Extended Feature registers. Must be value 0 during configuration
        ljm.eWriteName(self.handle, "%s_EF_ENABLE" % self.tr_sink_addr, 0)
        # Choose which extended feature to set
        ljm.eWriteName(self.handle, "%s_EF_INDEX" % self.tr_sink_addr, 12)
        # Set reset options, see bitmask options
        ljm.eWriteName(self.handle, "%s_EF_CONFIG_A" % self.tr_sink_addr, 0)  # 0: Falling edges , 1: Rising edges (<-i think, depends on bitmask)
        # NOTE: Not needed for our implementation: --> DIO2_EF_CONFIG_B,  DIO2_EF_CONFIG_C
        # Turn on the DIO-EF  --> Enable trigger once configs are done
        ljm.eWriteName(self.handle, "%s_EF_ENABLE" % self.tr_sink_addr, 1)

    # Step 8) Sets sends positional commands to
    def init_start_positions(self):
        rc = ljm.eWriteNames(self.handle, 2, [self.step_addr, self.sine_addr], [self.step_values[0], self.sine_values[0]])
        print("Setting start positions for Step and Sine values:", self.step_values[0],", ",  self.sine_values[0])

    def finalCheck(self):
        if len(self.aAddresses) != len(self.aValues):
            print("ERROR. NOT SAME COMMAND LIST LENGTHS")
            self.abort_scan = True

        for i in range(len(self.aAddresses)):
            if self.aAddresses[i] == self.tr_source_addr:
                if self.aValues[i] != 0 and self.aValues[i] != 1:
                    print("ERROR. INVALID VALUE FOR EDGE SOURCE VALUE")
                    self.abort_scan = True

            if self.aAddresses[i] == self.tr_sink_addr:
                print("ERROR. SINK SHOULD NOT BE A COMMAND TARGET ADDRESS")
                self.abort_scan = True

            if self.aAddresses[i] == self.wait_address:
                if self.aValues[i] < 100:
                    print("ERROR. VALUE TOO SMALL. LIKELY NOT ALIGNED")
                    self.abort_scan = True

            if self.aAddresses[i] == self.step_addr:
                if self.aValues[i] > 4:
                    print("ERROR. VALUE TOO BIG")
                    self.abort_scan = True

            if self.aAddresses[i] == self.sine_addr:
                print("ERROR. SINE IN COMMAND LIST")
                if self.aValues[i] > 4:
                    print("ERROR. VALUE TOO BIG")
                self.abort_scan = True

            if self.aAddresses[i] == self.q_M101_addr:
                if self.aValues[i] != 0 and self.aValues[i] != 1:
                    print("ERROR. QUTAG PING VALUE ERROR")
                    self.abort_scan = True

        if self.abort_scan:
            print("\nFinal Check Failed")
        else:
            print("Final Check Succeeded")

        # Step 9) Actual scan is done here

    def start_scan(self):
        # Start configured (but trigger-set) stream
        self.finalCheck()
        if self.abort_scan:
            rc = ljm.eWriteName(self.handle, self.tr_source_addr, 0)  # send 0 just in case to stop any input
            self.set_offset_pos()
            return

        # NOTE: HERE WE SET UP THE TRIGGER, AND WHEN WE ENTER THE "WriteNames()" WE SET IT TO LOW FOR A FALLING EDGE
        rc = ljm.eWriteName(self.handle, self.tr_source_addr, 1)

        scanRate = ljm.eStreamStart(self.handle, self.b_scansPerRead, self.b_nrAddresses, self.b_aScanList, self.b_scanRate)
        #print("Scan Rate:", self.b_scanRate, "vs.", scanRate)

        """        if self.useTrigger:
        print("")
        print("-------")
        print(f"Stream activated, but waiting. ")
        print(f"You can trigger stream now via a falling edge on {self.tr_source_addr}.\n")
        print("Sleeping 5 seconds to test trigger:")
        for i in range(1, 6):
            print(i, "s ...")
            time.sleep(1)"""
        print("ljm.WriteNames(...)")

        start_time = time.time()
        rc = ljm.eWriteNames(self.handle, len(self.aAddresses), self.aAddresses, self.aValues)
        end_time = time.time()

        # TODO: CHECK IF WE NEED TO CLEAR ANYTHING ELSE (due to trigger) WHEN STOPPING
        err = ljm.eStreamStop(self.handle)

        print(f"Expected scan time = {int(self.scanTime)} seconds")
        print("Actual scan time:", end_time - start_time)
        #print("Steam stop error (sine wave):", err)
        #print("WriteNames error (stepping):", rc)
        rc = ljm.eWriteName(self.handle, self.tr_source_addr, 0)  # send 0 just in case to stop any input
        self.set_offset_pos()

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
