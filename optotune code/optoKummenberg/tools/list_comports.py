# Uses pypiwin32
# For attribs, see: https://docs.microsoft.com/en-us/windows/win32/cimwin32prov/win32-serialport

import sys
import glob
import serial
from serial.tools import list_ports
# import win32com.client

def run():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


def get_ftdi_port():
    port = None

    devices = list_ports.comports()
    ##look for USB-CDC
    device = list([device.device for device in devices if '0483:A31E' in device.hwid])
    if not device:
        # look for CP2102
        device = list([device.device for device in devices if '10C4:EA60' in device.hwid])
        if not device:
            # look for FTDI
            device = list([device.device for device in devices if '0403:6001' in device.hwid])
    if device:
        port = device.pop()

    return port

if __name__ == '__main__':
    print(run())
