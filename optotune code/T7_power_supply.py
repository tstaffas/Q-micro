from labjack import ljm  #Allows communication with the labjack
import time
import numpy as np


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

        self.wait_address = "WAIT_US_BLOCKING" #"61590"


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

    def ping_FIO_sequence(self, port, time_delay, size,voltage = 1):
        adresses = []
        values = []

        for i in range(size):
            adresses.append([self.wait_address, port, port])
            values.append([time_delay, voltage, 0])

        ljm.eWriteNames(handle, len(names), names, values)
        
    
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

      
 
