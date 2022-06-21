r"""
Lookup tables / management of System registers specific to the MR-E-2.

Each System is represented by its own class, with Registers as attributes of that class.
The registers module can be imported to retrieve information about a given registers.
Syntax is as follows: registers.SYSTEM_NAME(CHANNEL_NUMBER).REGISTER_NAME

Returns
-------
dict
    A standard lookup will return a Register Record, or dictionary, containing pertinent registers information.

Notes
-----
A handful of helper methods are included to manage registers requests. See corresponding info for the following:
    is_valid_channel(value), is_valid_value(register_dict, value)
    tools.parsing_tools.encode(command_id, register_id)
    system_info()
    system_names()
    register_names(system_name)
    tools.systems_registers_tools.get_register(system_name, register_name, channel)
    parse_error(error_code)
    help()

Examples
--------

For example, this imports the registers module, and collects the registers record of USB channel 0, as well as the
registers record for setting the input channel system of the Signal Flow Manager.

    >>> from optoMDC.mre2 import Registers
    >>> Registers.StaticInput(0).of

    >>> Registers.StaticInput(0).of
    {'id': 20737, 'type': <class 'float'>, 'unit': None, 'range': [-1, 1], 'default': 0.0}
    >>> Registers.Manager(0).input
    {'id': 16384, 'type': <class 'int'>, 'unit': 'SystemID', 'range': None, 'default': None}
    >>> from optoMDC.tools.systems_registers_tools import is_valid_value
    >>> is_valid_value(Registers.StaticInput(0).xy, 0.8)
    True

Additional Notes
----------------
For more info on a given registers, see the help text in the corresponding System class.
This will display ID, Data Type, Units, Range, Default Value, and Comments.
    >>> Registers.SignalGenerator.help()

For a complete list of registers for a given system, call one of the helper methods from registers module itself.
    >>> Registers.get_registers(system_name='StaticInput', channel=1)


"""
from optoKummenberg.registers.generic_registers import *
from ..tools.definitions import MRE2_CHANNEL_CNT


# control mode
from ..tools.parsing_tools import parse_error_flags_mre2


class OFPID(ControlStage):
    r"""
Control Mode Channel - OF PID Control (with/without Temperature Compensation)
System ID: 0xB8 through 0xBf

+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| Register Name      | Id   | Type        | Unit | Range | Default | Comment                                          |
+====================+======+=============+======+=======+=========+==================================================+
|adaptive_pid_enabled| 0x00 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| kp                 | 0x01 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| ki                 | 0x02 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| kd                 | 0x03 |uint 32-bit  |bool  | T/F   | 1       |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| min_output         | 0x03 |float 32-bit |None  |       |         | If PID output reaches this, it is clamped to this|
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| max_output         | 0x04 |float 32-bit |None  |       |         | If PID output reaches this, it is clamped to this|
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| min_integral       | 0x05 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| max_integral       | 0x06 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| ap                 | 0x07 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| bp                 | 0x08 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| ai                 | 0x09 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| bi                 | 0x0a |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| ad                 | 0x0b |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| bd                 | 0x0c |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
    """

    # TODO: update these registers
    @staticmethod
    def help():
        print(OFPID.__doc__)

    def __init__(self, channel: int = 0, board=None):
        self.sys_id = 0xB8 | channel
        self._readonly = False

        self.adaptive_pid_enabled = {'id': self.sys_id << 8 | 0x00,
                                     'type': bool,
                                     'unit': None,
                                     'range': [True, False],
                                     'default': 1,
                                     'value': 1}
        self.kp = {'id': self.sys_id << 8 | 0x01,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 20.0,
                   'value': 20.0}
        self.ki = {'id': self.sys_id << 8 | 0x02,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 0.03,
                   'value': 0.03}
        self.kd = {'id': self.sys_id << 8 | 0x03,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 800.0,
                   'value': 800.0}
        self.min_output = {'id': self.sys_id << 8 | 0x04,
                           'type': float,
                           'unit': None,
                           'range': None,
                           'default': -1.0,
                           'value': -1.0}
        self.max_output = {'id': self.sys_id << 8 | 0x05,
                           'type': float,
                           'unit': None,
                           'range': None,
                           'default': 1.0,
                           'value': 1.0}
        self.min_integral = {'id': self.sys_id << 8 | 0x06,
                             'type': float,
                             'unit': None,
                             'range': None,
                             'default': 0,
                             'value': 0}
        self.max_integral = {'id': self.sys_id << 8 | 0x07,
                             'type': float,
                             'unit': None,
                             'range': None,
                             'default': 0,
                             'value': 0}
        self.ap = {'id': self.sys_id << 8 | 0x08,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 40.0,
                   'value': 40.0}
        self.bp = {'id': self.sys_id << 8 | 0x09,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 20.0,
                   'value': 20.0}
        self.ai = {'id': self.sys_id << 8 | 0x0a,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 0.06,
                   'value': 0.06}
        self.bi = {'id': self.sys_id << 8 | 0x0b,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 0.03,
                   'value': 0.03}
        self.ad = {'id': self.sys_id << 8 | 0x0c,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 8000.0,
                   'value': 8000.0}
        self.bd = {'id': self.sys_id << 8 | 0x0d,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 800.0,
                   'value': 800.0}

        ControlStage.__init__(self, channel, board)
        self.name = self.__class__.__name__


class XYPID(ControlStage):
    r"""
Control Mode Channel - XY PID Control (with/without Temperature Compensation)
System ID: 0xC0 through 0xC7

+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| Register Name      | Id   | Type        | Unit | Range | Default | Comment                                          |
+====================+======+=============+======+=======+=========+==================================================+
|adaptive_pid_enabled| 0x00 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| kp                 | 0x01 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| ki                 | 0x02 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| kd                 | 0x03 |uint 32-bit  |bool  | T/F   | 1       |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| min_output         | 0x04 |float 32-bit |None  |       |         | If PID output reaches this, it is clamped to this|
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| max_output         | 0x05 |float 32-bit |None  |       |         | If PID output reaches this, it is clamped to this|
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| min_integral       | 0x06 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| max_integral       | 0x07 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| ap                 | 0x08 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| bp                 | 0x09 |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| ai                 | 0x0a |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| bi                 | 0x0b |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| ad                 | 0x0c |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| bd                 | 0x0d |float 32-bit |None  |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+

    """

    # TODO: update these registers
    @staticmethod
    def help():
        print(XYPID.__doc__)

    def __init__(self, channel: int = 0, board=None):
        self.sys_id = 0xC0 | channel
        self._readonly = False

        self.adaptive_pid_enabled = {'id': self.sys_id << 8 | 0x00,
                                     'type': bool,
                                     'unit': None,
                                     'range': [True, False],
                                     'default': 1,
                                     'value': 1}
        self.kp = {'id': self.sys_id << 8 | 0x01,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 20.0,
                   'value': 20.0}
        self.ki = {'id': self.sys_id << 8 | 0x02,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 0.03,
                   'value': 0.03}
        self.kd = {'id': self.sys_id << 8 | 0x03,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 800.0,
                   'value': 800.0}
        self.min_output = {'id': self.sys_id << 8 | 0x04,
                           'type': float,
                           'unit': None,
                           'range': None,
                           'default': -1.0,
                           'value': -1.0}
        self.max_output = {'id': self.sys_id << 8 | 0x05,
                           'type': float,
                           'unit': None,
                           'range': None,
                           'default': 1.0,
                           'value': 1.0}
        self.min_integral = {'id': self.sys_id << 8 | 0x06,
                             'type': float,
                             'unit': None,
                             'range': None,
                             'default': 0,
                             'value': 0}
        self.max_integral = {'id': self.sys_id << 8 | 0x07,
                             'type': float,
                             'unit': None,
                             'range': None,
                             'default': 0,
                             'value': 0}
        self.ap = {'id': self.sys_id << 8 | 0x08,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 40.0,
                   'value': 40.0}
        self.bp = {'id': self.sys_id << 8 | 0x09,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 20.0,
                   'value': 20.0}
        self.ai = {'id': self.sys_id << 8 | 0x0a,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 0.06,
                   'value': 0.06}
        self.bi = {'id': self.sys_id << 8 | 0x0b,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 0.03,
                   'value': 0.03}
        self.ad = {'id': self.sys_id << 8 | 0x0c,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 8000.0,
                   'value': 8000.0}
        self.bd = {'id': self.sys_id << 8 | 0x0d,
                   'type': float,
                   'unit': None,
                   'range': None,
                   'default': 800.0,
                   'value': 800.0}

        System.__init__(self, channel, board)
        self.name = self.__class__.__name__
        if not is_valid_channel(self._channel):
            raise ValueError('Channel Range Error')


# memory systems
class MRE2MiscFeatures(System):
    """
Device Functionality - Misc
System ID: 0x25

+---------------------------+------+-------------+------+-------+---------+-------------------------------------------+
| Register Name             | Id   | Type        | Unit | Range | Default | Comment                                   |
+===========================+======+=============+======+=======+=========+===========================================+
| scuti_led                 | 0x00 |float 32-bit |None  |       |         |                                           |
+---------------------------+------+-------------+------+-------+---------+-------------------------------------------+
| disable_proxy_clock       | 0x01 |float 32-bit |None  |       |         |                                           |
+---------------------------+------+-------------+------+-------+---------+-------------------------------------------+
| ensable_proxy_clock       | 0x02 |float 32-bit |None  |       |         |                                           |
+---------------------------+------+-------------+------+-------+---------+-------------------------------------------+
| enable_cpu_led            | 0x03 |float 32-bit |None  |       |         |                                           |
+---------------------------+------+-------------+------+-------+---------+-------------------------------------------+
| disable_cpu_led           | 0x04 |float 32-bit |None  |       |         |                                           |
+---------------------------+------+-------------+------+-------+---------+-------------------------------------------+
| dump_fpga_mapped_memory   | 0x05 |float 32-bit |None  |       |         |                                           |
+---------------------------+------+-------------+------+-------+---------+-------------------------------------------+
| dump_eeprom_mapped_memory | 0x06 |float 32-bit |None  |       |         |                                           |
+---------------------------+------+-------------+------+-------+---------+-------------------------------------------+
| get_fpga_status_register  | 0x07 |float 32-bit |None  |       |         |                                           |
+---------------------------+------+-------------+------+-------+---------+-------------------------------------------+
    """

    def __init__(self, board=None):
        self.sys_id = 0x25
        self._readonly = False

        self.scuti_led = {'id': self.sys_id << 8 | 0x00,
                          'type': float,
                          'unit': None,
                          'range': [0, 2],
                          'default': 0.5,
                          'value': 0.5}
        self.disable_proxy_clock = {'id': self.sys_id << 8 | 0x01,
                                    'type': float,
                                    'unit': None,
                                    'range': None,
                                    'default': None,
                                    'value': None}
        self.enable_proxy_clock = {'id': self.sys_id << 8 | 0x02,
                                   'type': float,
                                   'unit': None,
                                   'range': None,
                                   'default': None,
                                   'value': None}
        self.enable_cpu_led = {'id': self.sys_id << 8 | 0x03,
                               'type': float,
                               'unit': None,
                               'range': None,
                               'default': None,
                               'value': None}
        self.disable_cpu_led = {'id': self.sys_id << 8 | 0x04,
                                'type': float,
                                'unit': None,
                                'range': None,
                                'default': None,
                                'value': None}
        self.dump_fpga_mapped_memory = {'id': self.sys_id << 8 | 0x05,
                                        'type': float,
                                        'unit': None,
                                        'range': None,
                                        'default': None,
                                        'value': None}
        self.dump_eeprom_mapped_memory = {'id': self.sys_id << 8 | 0x06,
                                          'type': float,
                                          'unit': None,
                                          'range': None,
                                          'default': None,
                                          'value': None}
        self.get_fpga_status_register = {'id': self.sys_id << 8 | 0x07,
                                         'type': float,
                                         'unit': None,
                                         'range': None,
                                         'default': None,
                                         'value': None}

        System.__init__(self, board=board)
        self.name = self.__class__.__name__

    def GetScutiLED(self):
        return self.get_register('scuti_led')

    def SetScutiLED(self, value):
        return self.set_register('scuti_led', value)

    def DisableProxyClock(self):
        return self.get_register('disable_proxy_clock')

    def EnableProxyClock(self):
        return self.get_register('enable_proxy_clock')

    def EnableCPULED(self):
        return self.get_register('enable_cpu_led')

    def DisableCPULED(self):
        return self.get_register('disable_cpu_led')

    def DumpFPGAMappedMemory(self):
        return self.get_register('dump_fpga_mapped_memory')

    def DumpEEPROMMappedMemory(self):
        return self.get_register('dump_eeprom_mapped_memory')

    def GetFPGAStatusRegister(self):
        return self.get_register('get_fpga_status_register')


class MRE2Status(Status):
    r"""
  Device Functionality - Firmware Status
  System ID: 0x10

  +---------------------+------+-------------+---------+---------------------------------------+
  | Register Name       | Id   | Type        | Default | Comment                               |
  +=====================+======+=============+=========+=======================================+
  | firmware_id         | 0x00 | float 32-bit|         |                                       |
  +---------------------+------+-------------+---------+---------------------------------------+
  | firmware_branch     | 0x01 | float 32-bit|         |                                       |
  +---------------------+------+-------------+---------+---------------------------------------+
  | fw_type             | 0x02 | float 32-bit|         |                                       |
  +---------------------+------+-------------+---------+---------------------------------------+
  | fw_version_major    | 0x03 | float 32-bit|         |                                       |
  +---------------------+------+-------------+---------+---------------------------------------+
  | fw_version_minor    | 0x04 | float 32-bit|         |                                       |
  +---------------------+------+-------------+---------+---------------------------------------+
  | fw_version_build    | 0x05 | float 32-bit|         |                                       |
  +---------------------+------+-------------+---------+---------------------------------------+
  | fw_version_revision | 0x06 | float 32-bit|         |                                       |
  +---------------------+------+-------------+---------+---------------------------------------+
  | error_flag_register | 0x07 | float 32-bit| 0       | See: Status Register Values Below     |
  +---------------------+------+-------------+---------+---------------------------------------+
  | proxy_fpga_version  | 0x08 | float 32-bit|         |                                       |
  +---------------------+------+-------------+---------+---------------------------------------+
  | cpu_fpga_version    | 0x09 | float 32-bit|         |                                       |
  +---------------------+------+-------------+---------+---------------------------------------+

  Status Register Values:

  ====== =================================================================
  Bit#   Message
  ====== =================================================================
  0      Proxy not connected
  1      Proxy temperature threshold is reached. See TemperatureManager
  2      Mirror temperature threshold is reached See TemperatureManager
  3      Mirror EEPROM not valid
  4      Mirror not stable. See stability criterion in OpticalFeedback
  5      Linear output limit is reached. See LinearOutput
  6      Linear output average limit is reached. See LinearOutput
  7      XY input is trimmed. See InputConditioning
  8      Proxy was disconnected
  9      Proxy temperature threshold was reached
  10     Mirror temperature threshold was reached
  11     Linear output limit was reached
  12     Linear output average limit was reached
  13     XY input was trimmed
  14..31 Reserved
  ====== =================================================================
      Write:
      Writing to this register resets all history error flags 8, 9, 10, 11, 12, 13
      """

    @staticmethod
    def help():
        print(MRE2Status.__doc__)

    _is_a_system = False

    def __init__(self, board=None):
        Status.__init__(self, board)

        self.proxy_fpga_version = {'id': self.sys_id << 8 | 0x08,
                                   'type': int,
                                   'unit': None,
                                   'range': None,
                                   'default': None,
                                   'value': None}
        self.cpu_fpga_version = {'id': self.sys_id << 8 | 0x09,
                                 'type': int,
                                 'unit': None,
                                 'range': None,
                                 'default': None,
                                 'value': None}
        self.name = self.__class__.__name__

    def GetProxyFPGAVersion(self):
        return self.get_register('proxy_fpga_version')

    def GetCPUFPGAVersion(self):
        return self.get_register('cpu_fpga_version')

    def parse_error_flags(self, error_flag_data: int):
        return parse_error_flags_mre2(error_flag_data)


class MRE2StaticInput(StaticInput):
    r"""
Input Channel Systems - USB/UART
System IDs: 0x50 through 0x57

+----------------+------+-------------+----------+-------------+---------+---------------------------------------+
| Register Name  | Id   | Type        | Unit     | Range       | Default | Comment                               |
+================+======+=============+==========+=============+=========+=======================================+
| current        | 0x00 | float 32-bit| A        | -0.7 to 0.7 | 0.0     |                                       |
+----------------+------+-------------+----------+-------------+---------+---------------------------------------+
| of             | 0x01 | float 32-bit| None     | -1 to 1     | 0.0     |                                       |
+----------------+------+-------------+----------+-------------+---------+---------------------------------------+
| xy             | 0x02    | float 32-bit| Degrees  | -1 to 1  | 0.0     |                                       |
+----------------+------+-------------+----------+-------------+---------+---------------------------------------+

    """

    @staticmethod
    def help():
        print(MRE2StaticInput.__doc__)

    def __init__(self, channel: int = 0, board=None):
        self.sys_id = 0x50 | channel
        self._readonly = False

        self.of = {'id': self.sys_id << 8 | 0x01,
                   'type': float,
                   'unit': None,
                   'range': [-1, 1],
                   'default': 0.0,
                   'value': 0.0}
        self.xy = {'id': self.sys_id << 8 | 0x02,
                   'type': float,
                   'unit': 'Degrees',
                   'range': [-1, 1],
                   'default': 0.0,
                   'value': 0.0}
        StaticInput.__init__(self, channel, board)
        self.name = self.__class__.__name__
        if not is_valid_channel(self._channel):
            raise ValueError('Channel Range Error')

    def SetOF(self, value):
        return self.set_register('of', value)

    def GetOF(self):
        return self.get_register('of')

    def SetAngle(self, value):
        print("This method has been deprecated, running SetXY(value)")
        return self.set_register('xy', value)

    def GetAngle(self):
        print("This method has been deprecated, running GetXY()")
        return self.get_register('xy')

    def SetXY(self, value):
        return self.set_register('xy', value)

    def GetXY(self):
        return self.get_register('xy')


class MRE2Analog(Analog):
    r"""
Input Channel Systems - Analog Input
System ID: 0x58 through 0x5f

+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| Register Name  | Id   | Type        | Unit               | Range       | Default | Comment                |
+================+======+=============+====================+=============+=========+========================+
| unit           |0x01  | uint 32-bit | None               |0 to 2       | 0       | See registers table 1  |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| minimm         |0x02  | float 32-bit| Volt               |             | 0       |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| maximum        |0x03  | float 32-bit| Volt               |             | 0       |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
|mapping_minimum |0x04  | float 32-bit| A / None / Degrees |             | 0       | Unit depends on 0x0301 |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
|mapping_maximum |0x05  | float 32-bit| A / None / Degrees |             | 0       | Unit depends on 0x0301 |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+


registers table 1:

+---------------------+-------+
| Analogue Input Unit | Value |
+=====================+=======+
| Current             | 0     |
+---------------------+-------+
| OF                  | 1     |
+---------------------+-------+
| XY                  | 2     |
+---------------------+-------+

    """

    @staticmethod
    def help():
        print(Analog.__doc__)

    def __init__(self, channel: int = 0, board=None):
        Analog.__init__(self, channel, board)
        self._unitranges = {'A': [-1, 1], None: [-1, 1], 'Degrees': [-25, 25]}

        self.unit = {'id': self.sys_id << 8 | 0x01,
                     'type': int,
                     'unit': ['A', None, 'Degrees'],
                     'range': {0: 'Current', 1: 'OF', 2: 'XY'},
                     'default': 0,
                     'value': 0}
        self.name = self.__class__.__name__
        if not is_valid_channel(self._channel):
            raise ValueError('Channel Range Error')


class MRE2SignalGenerator(SignalGenerator):
    r"""
Input Channel Systems - Signal Generator Channel
System ID for channel 0: 0x60

+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| Register Name  | Id   | Type        | Unit               | Range       | Default | Comment                |
+================+======+=============+====================+=============+=========+========================+
| unit           | 0x00 | uint 32-bit | None               | 0 to 1      |   1     | See registers table 1  |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| run            | 0x01 | bool        | bool               | True / False|   0     |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| shape          | 0x02 | uint 32-bit | None               | 0 to 3      |   0     | See registers table 2  |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| frequency      | 0x03 | float 32-bit| Hz                 |             |   0     |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| amplitude      | 0x04 | float 32-bit|                    |             |   0     |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| offest         | 0x05 | float 32-bit|                    |             |   0     |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| phase          | 0x06 | float 32-bit| Degrees            | 0 to 360    |   0     |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| cycles         | 0x07 |             |                    |             |  -1     |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| duty_cycle     | 0x08 |   float     |                    | 0 to 1      | 0.5     |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+


registers table 1:

+---------------+-------+
| Waveform Unit | Value |
+===============+=======+
| Current       | 0     |
+---------------+-------+
| OF            | 1     |
+---------------+-------+
| XY            | 2     |
+---------------+-------+

registers table 2:

+---------------+-------+
| Wavform Shape | Value |
+===============+=======+
| Sinusoidal    | 0     |
+---------------+-------+
| Triangular    | 1     |
+---------------+-------+
| Rectangular   | 2     |
+---------------+-------+
| Sawtooth      | 3     |
+---------------+-------+
| Pulse         | 4     |
+---------------+-------+

    """

    # TODO: range may depend on selected input units.
    @staticmethod
    def help():
        print(MRE2SignalGenerator.__doc__)

    def __init__(self, channel: int = 0, board=None):
        SignalGenerator.__init__(self, channel, board)
        self.unit = {'id': self.sys_id << 8 | 0x00,
                     'type': int,
                     'unit': None,
                     'range': {0: 'Current', 1: 'OF', 2: 'XY'},
                     'default': 0,
                     'value': 0}
        if not is_valid_channel(self._channel):
            raise ValueError('Channel Range Error')


class MRE2VectorPatternUnit(VectorPatternUnit):
    r"""
Input Channel Systems - Vector Pattern Unit
System ID: 0x68 through 0x6f

+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| Register Name  | Id   | Type        | Unit               | Range       | Default | Comment                |
+================+======+=============+====================+=============+=========+========================+
|unit            | 0x00 | uint 32-bit | None               | 0 - 2       | 0       | See registers table    |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
|run             | 0x01 | uint 32-bit | bool               | True / False| 0       |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
|start           | 0x02 | float 32-bit|                    |             |         |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
|end             | 0x03 | float 32-bit|                    |             |         |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
|frequency_speed | 0x04 | float 32-bit| None               |             |         |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
|min_speed       | 0x05 | float 32-bit| Hz                 |             |         |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
|max_speed       | 0x06 |             |                    |             |         |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
|cycles          | 0x07 |             |                    |             |         |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
|external_trigger| 0x08 | uint 32-bit | None               | 0 to 2      | 0       | 0=disabled             |
|                |      |             |                    |             |         | 1=rising/falling edge  |
|                |      |             |                    |             |         | 2=rising edge          |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| output         | 0x09 |   float     |                    |             |         |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+

registers table 1:

+---------------+-------+
| Waveform Unit | Value |
+===============+=======+
| Current       | 0     |
+---------------+-------+
| OF            | 1     |
+---------------+-------+
| XY            | 2     |
+---------------+-------+

    """

    @staticmethod
    def help():
        print(MRE2VectorPatternUnit.__doc__)

    def __init__(self, channel: int = 0, board=None, sys_id_base=0x68):
        VectorPatternUnit.__init__(self, channel, board)

        self.unit = {'id': self.sys_id << 8 | 0x00,
                     'type': int,
                     'unit': None,
                     'range': {0: 'Current', 1: 'OF', 2: 'XY'},
                     'default': 1,
                     'value': 1}
        self.name = self.__class__.__name__
        if not is_valid_channel(self._channel):
            raise ValueError('Channel Range Error')


# sensor systems
class OpticalFeedback(System):
    """
Device Functionality - Optical Feedback
System ID: 0x23

+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| Register Name | Id   | Type        | Unit | Range | Default | Comment                                          |
+===============+======+=============+======+=======+=========+==================================================+
| of_a          | 0x00 |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| of_b          | 0x01 |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| x             | 0x02 |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| y             | 0x03 |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| x_stability_a | 0x04 |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| x_stability_b | 0x05 |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| v_stability_a | 0x06 |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| v_stability_b | 0x07 |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| pd0           | 0x08 |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| pd1           | 0x09 |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| pd2           | 0x0a |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| pd3           | 0x0b |float 32-bit |None  |       |          |                                                 |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| fpd0          | 0x0c |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| fpd1          | 0x0d |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| fpd2          | 0x0e |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
| fpd3          | 0x0f |float 32-bit |None  |       |         |                                                  |
+---------------+------+-------------+------+-------+---------+--------------------------------------------------+
    """

    @staticmethod
    def help():
        print(OpticalFeedback.__doc__)

    _is_a_system = True

    def __init__(self, board=None):
        self.sys_id = 0x23
        self.of_a = {'id': self.sys_id << 8 | 0x00, 'type': float, 'unit': None, 'range': None, 'default': None,
                     'value': None}
        self.of_b = {'id': self.sys_id << 8 | 0x01, 'type': float, 'unit': None, 'range': None, 'default': None,
                     'value': None}
        self.x = {'id': self.sys_id << 8 | 0x02, 'type': float, 'unit': None, 'range': None, 'default': None,
                  'value': None}
        self.y = {'id': self.sys_id << 8 | 0x03, 'type': float, 'unit': None, 'range': None, 'default': None,
                  'value': None}
        self.x_stability_a = {'id': self.sys_id << 8 | 0x04, 'type': float, 'unit': None, 'range': None,
                              'default': 10000.0, 'value': None}
        self.x_stability_b = {'id': self.sys_id << 8 | 0x05, 'type': float, 'unit': None, 'range': None,
                              'default': 10000.0, 'value': None}
        self.v_stability_a = {'id': self.sys_id << 8 | 0x06, 'type': float, 'unit': None, 'range': None,
                              'default': 100000.0, 'value': None}
        self.v_stability_b = {'id': self.sys_id << 8 | 0x07, 'type': float, 'unit': None, 'range': None,
                              'default': 100000.0, 'value': None}
        self.pd0 = {'id': self.sys_id << 8 | 0x08, 'type': float, 'unit': None, 'range': None, 'default': None,
                    'value': None}
        self.pd1 = {'id': self.sys_id << 8 | 0x09, 'type': float, 'unit': None, 'range': None, 'default': None,
                    'value': None}
        self.pd2 = {'id': self.sys_id << 8 | 0x0a, 'type': float, 'unit': None, 'range': None, 'default': None,
                    'value': None}
        self.pd3 = {'id': self.sys_id << 8 | 0x0b, 'type': float, 'unit': None, 'range': None, 'default': None,
                    'value': None}
        self.fpd0 = {'id': self.sys_id << 8 | 0x0c, 'type': float, 'unit': None, 'range': None, 'default': None,
                     'value': None}
        self.fpd1 = {'id': self.sys_id << 8 | 0x0d, 'type': float, 'unit': None, 'range': None, 'default': None,
                     'value': None}
        self.fpd2 = {'id': self.sys_id << 8 | 0x0e, 'type': float, 'unit': None, 'range': None, 'default': None,
                     'value': None}
        self.fpd3 = {'id': self.sys_id << 8 | 0x0f, 'type': float, 'unit': None, 'range': None, 'default': None,
                     'value': None}

        System.__init__(self, board=board)
        self.name = self.__class__.__name__

    def GetOpticalFeedbackA(self):
        return self.get_register('of_a')

    def GetOpticalFeedbackB(self):
        return self.get_register('of_b')

    def GetAngleA(self):
        return self.get_register('angle_a')

    def GetAngleB(self):
        return self.get_register('angle_b')

    def GetPDValues(self):
        return self._board.get_value([self.pd0, self.pd1, self.pd2, self.pd3])

    def GetFilteredPDValues(self):
        return self._board.get_value([self.fpd0, self.fpd1, self.fpd2, self.fpd3])


class MRE2TemperatureManager(System):
    r"""
Device Functionality - Device Temperature Readout
System ID: 0x22

+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
| Register Name      | Id   | Type        | Unit | Range | Default | Comment                                          |
+====================+======+=============+======+=======+=========+==================================================+
|scuti_temperature   | 0x00 |uint 32-bit  |°C    |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
|proxy_temperature   | 0x01 |uint 32-bit  |°C    |       |         |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
|scuti_temp_threshold| 0x02 |uint 32-bit  |°C    |       | 65      |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+
|proxy_temp_threshold| 0x03 |uint 32-bit  |°C    |       | 65      |                                                  |
+--------------------+------+-------------+------+-------+---------+--------------------------------------------------+

    """

    @staticmethod
    def help():
        print(MRE2TemperatureManager.__doc__)

    _is_a_system = True

    def __init__(self, board=None):
        self.sys_id = 0x22

        self.scuti_temperature = {'id': self.sys_id << 8 | 0x00, 'type': int, 'unit': '°C', 'range': None,
                                  'default': None, 'value': None}
        self.proxy_temperature = {'id': self.sys_id << 8 | 0x01, 'type': int, 'unit': '°C', 'range': None,
                                  'default': None, 'value': None}
        self.scuti_temp_threshold = {'id': self.sys_id << 8 | 0x02, 'type': int, 'unit': '°C', 'range': None,
                                     'default': 65, 'value': 65}
        self.proxy_temp_threshold = {'id': self.sys_id << 8 | 0x03, 'type': int, 'unit': '°C', 'range': None,
                                     'default': 65, 'value': 65}

        System.__init__(self, board=board)
        self.name = self.__class__.__name__

    def GetScutiTemperature(self):
        return self.get_register('scuti_temperature')

    def GetProxyTemperature(self):
        return self.get_register('proxy_temperature')

    def GetScutiTemperatureThreshold(self):
        return self.get_register('scuti_temp_threshold')

    def GetProxyTemperatureThreshold(self):
        return self.get_register('proxy_temp_threshold')

    def SetScutiTemperatureThreshold(self, value):
        return self.set_register('scuti_temp_threshold', value)

    def SetProxyTemperatureThreshold(self, value):
        return self.set_register('proxy_temp_threshold', value)


def systems():
    all_systems = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    all_systems = list(zip(*all_systems))[1]
    sys_dict = {}
    for system in all_systems:
        if hasattr(system, '_is_a_system'):
            try:
                # init instance of each channel in system to get attributes
                for i in range(MRE2_CHANNEL_CNT):
                    sys_obj = system(channel=i)
                    sys_id = sys_obj.sys_id
                    reg_dict = dict(sys_obj.register_list)
                    sys_dict.update({sys_id: {'name': sys_obj.name, 'registers': reg_dict}})
            except TypeError:
                # system does not have multiple channels
                sys_obj = system()
                sys_id = sys_obj.sys_id
                reg_dict = dict(sys_obj.register_list)
                sys_dict.update({sys_id: {'name': sys_obj.name, 'registers': reg_dict}})
            except AttributeError:
                # abstract system, do not add to list. this shouldn't happen
                pass
    return sys_dict