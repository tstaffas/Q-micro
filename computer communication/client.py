# echo-client.py

import socket
import pickle
import os
import time
from ctypes import *

def socket_connection():
    HEADERSIZE = 10
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostname()
    host = '130.229.144.106'
    host = '130.237.35.233'
    s.connect((host, 55555))


    while True:
        full_msg = b''
        new_msg = True

        while True:
            msg = s.recv(16)
            if new_msg:
                print(f"new message length: {msg[:HEADERSIZE]}")
                msglen = int(msg[:HEADERSIZE])
                new_msg = False
                
            full_msg += msg
            
            if len(full_msg) - HEADERSIZE == msglen:
                print(pickle.loads(full_msg[HEADERSIZE:]))
                print(type(pickle.loads(full_msg[HEADERSIZE:])))
                new_msg = True
                full_msg = b''

                #When connection is made, return true value

def run_qutag(file, scan_time):
    #This function contains all the communication with the qutag
    #It should be run after the connection to the microscope is completed
    print('This is running the qutag')


    dll_name = 'C:/Users/vLab/Desktop/quTag code/64_bit_lib/tdcbase.dll'
    usbdll_name= 'C:/Users/vLab/Desktop/quTag code/64_bit_lib/FTD3XX.dll'

    qutag = cdll.LoadLibrary("C:/Users/vLab/Desktop/Lidar/quTag code/tdcbase.dll")#"tdcbase.dll")

    qutag.TDC_getVersion.restype=c_double
    print(qutag.TDC_getVersion())
    rc = qutag.TDC_init( -1 )
    print( "TDC_init", rc )
    rc = qutag.TDC_enableChannels(0xff) # Use all channels 
    print( "TDC_enableChannels", rc )

    rc = qutag.TDC_setFiveChannelMode(1)
    print("Set Five Channel Mode", rc)
    rc = qutag.TDC_configureFilter(5,3,0b00110) # (channel to filter, enumerator for filtertype (3=sync),0bchannelmask)
    print( "TDC_configureFilter", rc )

    folder = "C:\\Users\\vLab\\Desktop\\microscope\\"
    filename = folder + file + ".txt"

    #########
    print(filename)
    rc = qutag.TDC_writeTimestamps(filename.encode("utf-8"),0)#start acquisition  0 -> FILEFORMAT_ASCII: 1 -> FILEFORMAT_BINARY
    print( "TDC_writeTimestamps", rc )
    time.sleep(scan_time)
    rc = qutag.TDC_writeTimestamps("".encode("utf-8"),0)#stop acquisition
    print( "TDC_writeTimestamps", rc )
    rc = qutag.TDC_deInit()
    print('Done!')

def main():
    #setup the server
    #when it receives a connection start the measurements

    t = 1

socket_connection()
