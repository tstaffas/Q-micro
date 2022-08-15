# MICROSCOPE

import socket
import time
import pickle
from labjack import ljm  #Allows communication with the labjack
import labjack
import optoMDC
import numpy as np


def socket_connection(file,scantime):
    
    HEADERSIZE = 10

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostname()
    #host = '130.237.35.233'
    host = '10.200.59.150'
    s.bind((host,55555))
    s.listen(5)

    print(f'Setting up the server at: {host}')
    while True:
        clientsocket, address = s.accept()
        print(f'Connection from {address} has been established!')

        msg = 'welcome to the server!'
        msg = pickle.dumps(msg)
        msg = bytes(f'{len(msg):<{HEADERSIZE}}',  'utf-8')+msg
        clientsocket.send(msg)

        #Send the message to start the measurement
        #filename = 'filename'
        #scantime = 5
        
        msg = {'file':file, 'scantime':scantime}
        msg = pickle.dumps(msg)
        msg = bytes(f'{len(msg):<{HEADERSIZE}}',  'utf-8')+msg
        clientsocket.send(msg)

        
        #clientsocket.close()

    #returns a value when it gets a connection

        


def scan_function():
    #This function should contain all the calls to the scanning mirror and the labjack
    print('This scans the mirror')
    
    ## Labjack functions
    class T7:
        def __init__(self):
            """
            Creates a connection with a T7 labjack connected in any port.
            Also creates some constants to be used later
            """
        
            self.handle = ljm.openS("T7", "Any", "ANY") #Connects with a T7 labjack in "ANY" port
            self.info = ljm.getHandleInfo(self.handle)

    
            #Constant, they save space
            self.WRITE = ljm.constants.WRITE
            self.READ = ljm.constants.READ
            self.FLOAT32 = ljm.constants.FLOAT32  #Currently the only one used
            self.UINT16 = ljm.constants.UINT16
            self.UINT32 = ljm.constants.UINT32

        def set_output(self, ID, v):
        #Sets the output of the TICDAC to a value between +/- 10
        #ID specifies which port the output is on

            if np.abs(v) < 10:
                dataType = self.FLOAT32
                ljm.eWriteAddress(self.handle, ID, dataType, v)

            else:
                print("Error: voltage limit exceded (you idiot)")


        def ping_FIO(self, port, time_delay=0, voltage = 1):
            """
            Sends a quick signal in the port, used to communicate with the hydra harp
            """

            #Different command then eWriteAddress, not entirely sure why
            ljm.eWriteName(self.handle, port, voltage)
            time.sleep(time_delay) #Might slow down the program
            ljm.eWriteName(self.handle, port, 0)

        def ping_DAC(self,address,v,time_delay=0):
            """
            Sends a quick signal in the adress, used to communicate with the hydra harp
            """
        
            dataType = self.FLOAT32
            ljm.eWriteAddress(self.handle, address, dataType, v)
            time.sleep(time_delay)
            ljm.eWriteAddress(self.handle, address, dataType, 0)
        

            def close(self):
                ljm.close(self.handle) #Shuts off the connection with the labjack
    """
    driver = T7()
    
    driver.ping_FIO("FIO2", 0.5)
    driver.close()
    """


    ## Initialization of the Mirror
    mre2 = optoMDC.connect()
    mre2.set_value(0xC014, float(200)) # lower the cutoff frequency for the low pass filter that affects derivative control action


    ch_1 = mre2.Mirror.Channel_1

    ch_1.InputConditioning.SetGain(1.0)                 
    ch_1.SetControlMode(optoMDC.Units.CURRENT)
    ch_1.LinearOutput.SetCurrentLimit(0.7)               

    sg_1 = mre2.Mirror.Channel_1.SignalGenerator
    sg_1.SetUnit(optoMDC.Units.CURRENT)                 
    sg_1.SetShape(optoMDC.Waveforms.SINUSOIDAL)         
    sg_1.SetAmplitude(0.06)
    sg_1.SetFrequency(1)   # change                                 

    ch_1.Manager.CheckSignalFlow()


    ch_0 = mre2.Mirror.Channel_0

    ch_0.SignalGenerator.SetAsInput()                   
    ch_0.StaticInput.SetAsInput()
    ch_0.InputConditioning.SetGain(1.0)                  
    ch_0.SetControlMode(optoMDC.Units.CURRENT)           
    ch_0.LinearOutput.SetCurrentLimit(0.7)               

    ch_0.Manager.CheckSignalFlow()

    sg_0 = mre2.Mirror.Channel_0.SignalGenerator
    sg_0 = mre2.Mirror.Channel_0.StaticInput

    # Scan settings      
    startpos = 0.01 # max value is 0.7   
    endpos = 0.016
    stepnumber = 10

    stepsize = (endpos - startpos)/stepnumber

    amp = np.linspace(startpos,endpos,stepnumber)
    sg_1.Run()

    ## Initialization of the Labjack
    #self = # serial number ?
    #__init__(self)      # open connection with Labjack
    LJ = T7()
    X_port =  'FIO2'
    Y_port =  'FIO3'
    X_address = 1000    # DAC0
    Y_address = 1002    # DAC1
    v = 1

    for a in amp:
        LJ.ping_FIO(X_port, time_delay=0.0, voltage = 1)     # 1st marker in port and address for the X axis
        LJ.ping_DAC(X_address,v,time_delay=0)
        sg_0.SetCurrent(a)
        start_time = time.time()
        seconds = 2 # change
        while a < endpos:
            current_time = time.time()
            elapsed_time = current_time - start_time
            LJ.ping_FIO(Y_port, time_delay=0.0, voltage = 1)     # 2nd marker in port and address
            LJ.ping_DAC(Y_address,v,time_delay=0)
            if elapsed_time > seconds:
                break
    sg_0.SetCurrent(0) 
    time.sleep(3)
    sg_1.SetAmplitude(0)
    
    LJ.close()        # end connection with Labjack


def main():
    #setup the server
    #when it receives a connection start the measurements
    #and wait for it to connect
    file = "analysis"
    scantime = 80              #duration of the scan on the microscope

    socket_connection(file,scantime)         #set up a server to communicate with the client (qutag)
    time.sleep(10)              #waits for 10 secs

    scan_function()             #starts the scan
    
    print('Done')
    
