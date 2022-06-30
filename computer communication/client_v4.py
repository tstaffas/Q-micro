# QUTAG

import socket
import pickle
import os
import time
from ctypes import *

def socket_connection():
    HEADERSIZE = 10
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostname()
    #host = '130.229.144.106'
    host = '130.237.35.233'
    s.connect((host, 55555))


    run_flag1 = True
    while run_flag1:
        full_msg = b''
        new_msg = True

        run_flag2 = True
        while run_flag2:
            msg = s.recv(16)
            if new_msg:
                #print(f"new message length: {msg[:HEADERSIZE]}")
                msglen = int(msg[:HEADERSIZE])
                new_msg = False
                
            full_msg += msg
            
            if len(full_msg) - HEADERSIZE == msglen:
                #print(pickle.loads(full_msg[HEADERSIZE:]))
                #print(type(pickle.loads(full_msg[HEADERSIZE:])))
                msg_sent = pickle.loads(full_msg[HEADERSIZE:])
                

                if type(msg_sent) == dict:     # checking if the message is in the proper form
                    # Recuperation of the data sent
                    msg_sent = pickle.loads(full_msg[HEADERSIZE:])
                    file = msg_sent['file']
                    scantime = msg_sent['scantime']

                    #Message received
                    print("Parameters received")
                    run_flag1 = False
                    run_flag2 = False
                    return file, scantime
                
                else:
                    print(msg_sent)
                    new_msg = True
                    full_msg = b''
                #    return('Error : the message sent is not a dictionnary')
                    

    
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
    filename = folder + file + ".timres"

    #########
    print(filename)
    rc = qutag.TDC_writeTimestamps(filename.encode("utf-8"),1)#start acquisition  0 -> FILEFORMAT_ASCII: 1 -> FILEFORMAT_BINARY
    print( "TDC_writeTimestamps", rc )
    time.sleep(scan_time)
    rc = qutag.TDC_writeTimestamps("".encode("utf-8"),0)#stop acquisition
    print( "TDC_writeTimestamps", rc )
    rc = qutag.TDC_deInit()
    print('Done!')

def dummy_function(file, scantime):
    #This function allows us to quickly test the communication between the two computers
    #without using the qutag functions
    print('This is running a dummy function to test the communication')
    print('Here are the informations sent by the qutag computer')
    print(file)
    print(scantime)
    print('Done')
    
def main():
    #setup the server
    #when it receives a connection start the measurements
    data = socket_connection()  #connects to the server and receive the data
    f = data[0]                 # file
    s = data[1]                 # scantime
    dummy_function(f, s)
    #run_qutag(f,s)       #starts the measurement

    print('Done')
    

main()
