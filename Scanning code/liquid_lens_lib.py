#!/usr/bin/env python
# -*- coding: utf-8 -*-

import serial
import time


# NOTE on microscope setup ------
#  * Electrically tunable lens: EL-16-40-TC (5D) or (20D)   # FIXME -> check which one
#       * Datasheet (5D): https://static1.squarespace.com/static/5d9dde8d550f0a5f20b60b6a/t/64393a1cfe30773d7abd77f1/1681472030722/Optotune-EL-16-40-TC.pdf
#       * Datasheet (20D): https://static1.squarespace.com/static/5d9dde8d550f0a5f20b60b6a/t/634465a227679a3694622ab4/1665426852887/Optotune+EL-16-40-TC-VIS-20D.pdf
#
#  * Lens Driver 4i:
#       * Manual: https://static1.squarespace.com/static/5d9dde8d550f0a5f20b60b6a/t/63cfdb005b3c212d742d60f8/1674566414045/Optotune+Lens+Driver+4+manual.pdf
#       * Firmware utility: https://static1.squarespace.com/static/5d9dde8d550f0a5f20b60b6a/t/5f85a77d3ef8c601436c3b9e/1602594713578/Optotune-Lens-Driver-Firmware-Flash-Utility.pdf
#           - IMPORTANT: we use firmware type "F" for EL-16-40 device
#       * Current control range: +/- 290 mA  (with 12 bit precision)
# -------------------------------------
# ----- other github solutions based on same material: -----
#  https://github.com/ha0k/pyopto/blob/master/pyopto.py
#  https://github.com/OrganicIrradiation/opto/blob/master/opto.py
# --------------------------------------------------------

# TODO:
#  - KeyInterupt Error: add close() call
#  - check all limits you set
#  - fix except: --> remove stuff so it goes to __Exit__
#  - check serial.Serial() documentation
#  - test connecting and reading  --> write some test commands
#  - ask what would happen is temp limits exceed. Does it auto shut off?
#  - go through final TODOs and FIXMEs before testing

"""
from liquid_lens_lib.py import opto_lib
o = opto_lib.OptoLens("COM5")    # connect to lens driver on COM4

if o.opto_lib.check_current_values(values, wait_value):   # IF ALL VALUES ARE OK
    o.current(values[0])      # set lens current to an already accepted value in list, example: values[0]
    
o.current(100)      # example: set lens current to 100mA
o.close()           # close connection with lens driver
"""

class OptoLens:    # NOTE: Implementation only for 'Mode=Current'

    # Constant hardware limits:   note: consult documentation if you want to change!!
    i_c = 292.84            # {{Warning: do not change}}  Maximum hardware current (unit mA), aka: "calibration value"
    step_tolerance = 50     # (<-chosen value) Device max current step we can take to be a gentle transition  # TODO: check for good value
    wait_tolerance = 0.02   # (<-chosen value) Shortest time step (unit s) between current changes. Lens specs: response time = 5ms, settling time = 25ms  # TODO: decide good value
    max_temp = 45           # (<-chosen value) Operating temp: -20°C to 65°C

    def __init__(self, port):
        print(f"\n-----------\nInitializing OptoLens:\n")
        self.lens_current = None        # TODO: define as: None or 0            # Current sent to lens driver 4
        self.lens_handle = None                      # USB serial handle for lens driver 4
        #self.lens_is_connected = False               # if we are connected to lens driver 4 (=True after handshake)

        # TODO: check how to get port. for example: port='COM4' or port='/dev/cu.usbmodem1411'
        self.connect(port)                          # open connection to lens driver and do handshake
        self.crc_table = self._build_crc16ibm_table()   # calculate crc table for later crc calculations
        self.check_device_configs( temp=True)        # status=False, mode=False, temp_lim=False, temp=False, current_lim=False

    def __exit__(self):   # TODO:check
        # NOTE: I think this is where we end up when there is a raise
        print("closing in __exit()__")
        self.close()

    #DONE
    def _send_cmd(self, cmd_list, has_response=False):
        # Send command to Lens Driver, return response if prompted

        # CHECK FOR CONNECTION:
        if (not self.lens_handle) or (not self.lens_handle.is_open):
            raise serial.SerialException('Serial port not connected')
            #raise Exception("Serial port is not connected. Please connect first.")

        # COMPUTE AND ADD CRC TO CMD LIST:          (source: converted from C# code): https://static1.squarespace.com/static/5d9dde8d550f0a5f20b60b6a/t/63cfdb005b3c212d742d60f8/1674566414045/Optotune+Lens+Driver+4+manual.pdf
        """ Example:   
            cmd_list     = {data byte 0, data byte 1, data byte 2}
            cmd_with_crc = {data byte 0, data byte 1, data byte 2, crc&0xFF, crc>>8} """

        crc = self.compute_crc(cmd_list)  # 16-bit unsigned integer
        cmd_with_crc = cmd_list + int(crc).to_bytes(2, byteorder='little')
        """#low_crc = crc & 0xFF                    # low CRC byte  (right half of crc)  & 0xFF  only keeps the last 8 bits -->  https://stackoverflow.com/questions/14713102/what-does-and-0xff-do
        #high_crc = crc >> 8                     # high CRC byte (left half of crc)   >> 8    bit shifting 8 spots       --> https://www.interviewcake.com/concept/java/bit-shift
        #cmd_with_crc_part = cmd_list + int(low_crc).to_bytes(1, byteorder='big') + int(high_crc).to_bytes(1, byteorder='big')
        #print(cmd_with_crc_part)
        #print(cmd_with_crc)
        #print(int(crc).to_bytes(2, byteorder='little')," = ", int(low_crc).to_bytes(1, byteorder='little')," + ",  int(high_crc).to_bytes(1, byteorder='little'), " --> ", cmd_with_crc)
        """

        """#byte_list = [b.to_bytes(1, byteorder='big') for b in cmd_list]
                #print(byte_list)
                #cmd_with_crc = byte_list.copy()           # byte list
                #cmd_with_crc.append(crc & 0xFF)          # low CRC byte  (right half of crc)  & 0xFF  only keeps the last 8 bits -->  https://stackoverflow.com/questions/14713102/what-does-and-0xff-do
                #cmd_with_crc.append(crc >> 8)            # high CRC byte (left half of crc)   >> 8    bit shifting 8 spots       --> https://www.interviewcake.com/concept/java/bit-shift
                #print(cmd_with_crc)"""

        # CHECK CHECKSUM ERROR (in command):
        if self.compute_crc(cmd_with_crc) != 0:  # CRC is correct if checksum calculation (over whole array) is equal to zero
            print(f"Failure: CRC checksum = {self.compute_crc(cmd_with_crc)} != 0")
            raise Exception("CRC validation failed.")  # raise (serial.SerialException(...))
        else:
            print("Success: CRC checksum of cmd = 0")  # FIXME: remove print later

        # WRITE COMMAND TO DRIVER:
        self.lens_handle.write(cmd_with_crc)

        # HANDLE RESPONSE FROM COMMAND:
        if has_response:
            reply = self.lens_handle.readline()  # note: <-- using readline() means we get /r/n at end    #reply = self.lens_handle.read_until('\r\n')  gives the same
            reply = reply[:-2]

            # Check if crc error in response:
            if  self.compute_crc(reply) != 0:
                print("Error: CRC at read failed:", reply, ", with checksum:", self.compute_crc(reply[:-2]))
                raise Exception("CRC validation failed.")  # raise (serial.SerialException(f"CRC mismatch: {resp}"))
            else:
                print("No crc error in response: ", reply)

            # Check if error code in response:
            if reply[0] == b'E':
                raise Exception("Error in write command.")  # raise (serial.SerialException('Command error: {}').format(resp_content))

            return reply

    # DONE
    def _build_crc16ibm_table(self):
        """
        source (converted from C# code in):
            https://static1.squarespace.com/static/5d9dde8d550f0a5f20b60b6a/t/63cfdb005b3c212d742d60f8/1674566414045/Optotune+Lens+Driver+4+manual.pdf
        """
        table = []  # table of len 256 with 16 bit ints
        for i in range(256):  # for(ushort i = 0 i < table.Length ++i)
            value = 0  # ushort
            temp = i  # ushort
            for j in range(8):
                if ((value ^ temp) & 0x0001) != 0:
                    value = (value >> 1) ^ 0xA001
                else:
                    value >>= 1
                temp >>= 1
            table.append(value)
        return table

    # NOTE: Safety check of generated current values  # NOTE: SHOULD DO THIS TEST BEFORE CONNECTING TO LENS DRIVER!!!
    def check_current_values(self, values, wait_value):
        """ returns empty list if safety test fails"""
        abort = False

        # TEST 1: Double-checking that max and min values defined in __init__ are ok
        if self.i_c >= 293:
            print(f"WARNING: Maximum hardware current (calibration value) is too high!")
            abort = True

        # TEST 2: Check if wait value (should be in ms) to low
        if wait_value < self.wait_tolerance:
            print(
                f"Error: Wait value too short: (value) {wait_value * 1000} ms < {self.wait_tolerance * 1000} ms (minimum)")
            abort = True

        # TEST 3: Checks all values in provided list
        #   NOTE: Currently assumes that we start at 0mA before scan. This might change if we start at a negative value.
        values_new = [0] + values  # combine lists to also check first step size.
        for i, val in enumerate(values):
            # check if value is in allowed range
            if abs(val) > 280:
                print(f"Error: Value {val} with index {i} is outside or too close to allowed range: +/- 283 mA")
                abort = True

            # check if change in current is too drastic.
            if abs(values_new[i] - values_new[i - 1]) > self.step_tolerance:
                print(
                    f"Error: Step between current values is too large. Step {abs(values_new[i] - values_new[i - 1])} > {self.step_tolerance}")
                abort = True

        if abort:
            # return []
            print("Aborting. Bad values...")
            return False  # abort scan
        else:
            print("Current check succeeded.")
            # return values
            return True

    #DONE
    def connect(self, port):   # to get port name --> check device manager
        """Connect to the device via serial port."""
        # PORT CONFIG:
        try:
            self.lens_handle = serial.Serial()
            self.lens_handle.port = port
            self.lens_handle.baudrate = 115200
            # note: ( bytesize = 8, parity = None, stop bits = 1 ) are already set as default!
            self.lens_handle.timeout = 0.2          # TODO: check value, unsure

            self.lens_handle.open()  # --> self.lens_handle.is_open = True
            # ^ lens handle after opening: Serial<id=0x1d648983e80, open=True>(port='COM5', baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=0.2, xonxoff=False, rtscts=False, dsrdtr=False)

            print("Lens Driver connected! Serial port:" + port)
        except serial.SerialException:
            raise serial.SerialException(f"Error: failed to open port: {port}.")

        # HANDSHAKE:
        #   Note: can be also used as a reset function (reset current to zero)
        try:
            if not self.lens_handle:
                raise serial.SerialException('Serial port not connected')

            self.lens_handle.write(b'Start')
            reply = self.lens_handle.readline()  # = self.lens_handle.read_until('\r\n')

            if reply[0] == b'E':
                raise serial.SerialException("Error in write command.")  # raise Exception( ... )

            if reply != b'Ready\r\n':   # maybe add bool to know if handshake succeeded
                print("Error: Handshake failed!")
                raise serial.SerialException('Handshake failed')

            print("Handshake successful!")
        except serial.SerialException:
            self.close()
            print("Error: Could not connect to serial port")
            raise

    #DONE
    def check_device_configs(self, status=False, mode=False, temp_lim=False, temp=False, current_lim=False):
        # Check set limits and change if needed:
        # -------- Check device STATUS: --------
        if status:   # firmware status information
            res_s = self._send_cmd(b'Sr', has_response=True)
            print("Device Status:\n", res_s[1:])  # print device status

        # -------- Check MODE: -----------------
        if mode:    # ensure node is set to 'D' (aka current)
            res_m = self._send_cmd(b'MrMA', has_response=True)   # TODO: check if we need the 'r' read indicator
            if res_m[3] != 1:   # 1 == 'D' == 'current mode'                # TODO: check if correct index!!
                # WRITE MODE:
                res_m = self._send_cmd(b'MwDA', has_response=True)
                print("Response (write mode):", res_m)
                if res_m[1] != ord(b'D'):                                   # TODO: check if correct!
                    raise Exception("Failed to set mode.")
            else:
                print("Mode: Current 'D' (index 1)")

        # -------- Check TEMP LIMITS -----------
        if temp_lim:
            res_temp_lim = self._send_cmd(b'PrTA\x00\x00\x00\x00', has_response=True)
            # TODO: check which one is which below!!
            res_low_lim = int.from_bytes(res_temp_lim[2:4], byteorder='big', signed=True) / 16
            res_high_lim = int.from_bytes(res_temp_lim[4:6], byteorder='big', signed=True) / 16
            print(f"Device temp limits set to: {res_low_lim} and {res_high_lim}")
            #if change:  # FIXME! and check first in docs
            #    data = (new_low_temp * 16).to_bytes(2, byteorder='big', signed=True) + (new_high_temp * 16).to_bytes(2, byteorder='big', signed=True))
            #    res = self._send_cmd(b'PwTA' + data, has_response=True)

        # -------- Check device TEMP -----------
        if temp:
            res = self._send_cmd(b'TCA', has_response=True)
            device_temp = int.from_bytes(res[3:5], byteorder='big', signed=True) * 0.0625
            print("Lens temp at:", device_temp)
            if device_temp > self.max_temp:
                raise Exception("Device temp too high:", device_temp, "degrees")

        # -------- Check CURRENT LIMITS --------
        if current_lim:
            # TODO: maybe bring back limit checker methods
            pass

    #  TODO look into 0x00ff and decide if we need it
    def compute_crc(self, byte_list):
        """
        source (converted from C# code in):
            https://static1.squarespace.com/static/5d9dde8d550f0a5f20b60b6a/t/63cfdb005b3c212d742d60f8/1674566414045/Optotune+Lens+Driver+4+manual.pdf

            cmd_list: b'Aw\x00\x00'
            Bytes:   0x41, 0x77, 0x0, 0x0
            byte_1: 0x41   -->  index:  65
            byte_2: 0x77   -->  index:  183
            byte_3: 0x0   -->  index:  112
            byte_4: 0x0   -->  index:  119
        """
        # TODO: maybe make dictionary instead of table

        crc = 0  # initial CRC value
        i = 0
        for byte_i in byte_list:
            i += 1
            #index = crc ^ byte_i
            index = (crc ^ byte_i) & 0xFF     # doesn't seem to work without 0x00ff -> read about 0xFF  https://stackoverflow.com/a/4174702
            #print(f"byte_{i}:", hex(byte_i), "  -->  index: ", index)
            crc = (crc >> 8) ^ self.crc_table[index]

        #crc_b1 = crc.to_bytes(2, byteorder='little')  # TODO: check!
        #crc_b2 = crc.to_bytes(2, byteorder='big')  # TODO: check!
        #print("CRC bytes:  ", crc_b1, "?=(big)", crc_b2, "?=", ", ".join(hex(b) for b in crc_b1))
        #return crc_b2  # returns checksum (=unsigned 16-bit integer) over all elements
        return crc

    # DONE
    def current(self, i_o=None):
        """Read/Write: Current.
            Hardware limits:  -293 mA < value < 293 mA
            Args: i_o = desired current [mA]
        """
        print("")

        if i_o is None:  # READ LENS CURRENT
            r_response = self._send_cmd(b'Ar\x00\x00', has_response=True)
            print("Read current response:", r_response)

            x_i = int.from_bytes(r_response[1:-2], byteorder='big', signed=True)   # TODO: if correct index

            i_o_res = x_i * self.i_c / 4096
            print("Response (read current):", i_o_res, f" (taken from data bytes x_i: {r_response[1:-2]} == {x_i})")
            return i_o_res

        else:  # WRITE LENS CURRENT
            if abs(i_o) >= self.i_c:
                print("Error: too high current detected!! Exiting out.")
                raise Exception("Tried to write out of bounds current value")
            else:
                x_i = (i_o / self.i_c) * 4096
                print(f"Writing: {i_o} mA --> x_i = {x_i}")
                if abs(x_i) < 4090:   # +/- 4096 is the limit
                    byte_val = int(x_i).to_bytes(2, byteorder='big', signed=True)
                    w_response = self._send_cmd(b'Aw' + byte_val, has_response=False)

                    print("Response (write current):", w_response)
                    self.lens_current = i_o
                else:
                    print("WOAH! NOH")
                return i_o

    # DONE
    def close(self):
        """Close serial connection with Lens Driver. Decrease current gradually to 0."""
        print("Closing lens driver connection...")
        #if self.lens_handle.is_open:   # TODO: maybe use this instead
        if self.lens_current:#   If we have an applied current: gradually step down softly at shutdown
            exit_current = self.lens_current
            i = 0
            while abs(exit_current) > 30:    # decrease softly until
                exit_current = exit_current / 2

                i += 1  # only used to print
                print(f"Exit current {i}: {exit_current}")

                # safety check on some soft limit (maybe can remove after testing)
                if abs(exit_current) > 230:
                    print("ERROR: Exit current out of bounds!")
                    raise ValueError("Exit current OOB")

                self.current(exit_current)
                time.sleep(0.1)  # unit seconds         TODO: Check for suitable value
            self.current(0)  # exit with no current in lens
        self.lens_handle.close()
        self.lens_handle = None   # del self.lens_handle  # TODO: find out why we would want to delete this. and what happens when we do
        self.lens_current = None
        #self.lens_is_connected = False


class _Hidden:
    # maaayyybbbbbeee, yes we want these, or at least for double-checking that configs are default.

    def _software_current_limits(self):  # TODO: check conversion!
        """Get (and maybe set) upper or lower software current limit.
                --> Software current limit: default = 4096
                    (automatically adjusts, so we don't send values outside defined limits)
        """
        pass

        #c_lower_res = self._send_cmd(b'CrLA\x00\x00', has_response=True)
        #current_lower_lim = int.from_bytes(c_lower_res[3:5], byteorder='big', signed=True) * self.i_c / 4096   # TODO: check
        #print(f"Software current lower limit = {current_lower_lim}")

        #c_upper_res = self._send_cmd(b'CrUA\x00\x00', has_response=True)
        #current_upper_lim = int.from_bytes(c_upper_res[3:5], byteorder='big', signed=True) * self.i_c / 4096   # TODO: check
        #print(f"Software current upper limit = {current_upper_lim}")

        #return #current_lower_lim, current_upper_lim

    def _max_hardware_current_i_c(self):
        """Read: "Maximum hardware output current" (aka: "calibration value" i_c)
                i_c : default = 292.84 mA
                NOTE: It is not recommended to write a different value to this
        """
        pass
        #res = self._send_cmd(b'CrMA\x00\x00', has_response=True)
        #i_c = int.from_bytes(res[3:5], byteorder='big', signed=True) / 100
        #return i_c
