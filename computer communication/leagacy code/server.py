# echo-server.py

import socket
import time
import pickle 

def socket_connection():
    
    HEADERSIZE = 10

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostname()
    host = '130.237.35.233'
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
        filename = 'filename'
        scantime = 5
        
        msg = {'filename':filename, 'filename':scantime}
        msg = pickle.dumps(msg)
        msg = bytes(f'{len(msg):<{HEADERSIZE}}',  'utf-8')+msg
        clientsocket.send(msg)

        
        #clientsocket.close()

    #returns a value when it gets a connection

        


def scan_function():
    #This function should contain all the calls to the scanning mirror and the labjack
    print('This scans the mirror')




def main():
    #setup the server
    #when it receives a connection start the measurements

    
    #and wait for it to connect
    print('Done')
socket_connection()
