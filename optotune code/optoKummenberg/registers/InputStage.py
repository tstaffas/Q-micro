from .ClassAbstracts import InputStage
from ..tools.systems_registers_tools import is_valid_channel
from ..tools.definitions import UnitType
from .generic_registers import get_registers


class SPI(InputStage):
    r"""
Input Channel Systems - SPI
System ID: 0x48 through 0x4f

+----------------+------+-------------+----------+--------+---------+---------------------------------------+
| Register Name  | Id   | Type        | Unit     | Range  | Default | Comment                               |
+================+======+=============+==========+========+=========+=======================================+
| input          | 0x01 | uint 32-bit | None     | 0 to 5 | 0       | For both channel. See registers table |
+----------------+------+-------------+----------+--------+---------+---------------------------------------+

    """

    @staticmethod
    def help():
        print(SPI.__doc__)

    def __init__(self, channel: int = 0, board=None):
        self.sys_id = 0x48 | channel
        self._readonly = False

        self.input = {'id': self.sys_id << 8 | 0x01,
                      'type': int,
                      'unit': None,
                      'range': [0, 5],
                      'default': 0,
                      'value': 0}
        InputStage.__init__(self, channel, board)
        self.name = self.__class__.__name__
        if not is_valid_channel(self._channel):
            raise ValueError('Channel Range Error')

    def SelectInput(self, value):
        return self.set_register('input', value)


class StaticInput(InputStage):
    r"""
Input Channel Systems - USB/UART
System IDs: 0x50 through 0x57

+----------------+------+-------------+----------+-------------+---------+---------------------------------------+
| Register Name  | Id   | Type        | Unit     | Range       | Default | Comment                               |
+================+======+=============+==========+=============+=========+=======================================+
| current        | 0x00 | float 32-bit| A        | -0.7 to 0.7 | 0.0     |                                       |
+----------------+------+-------------+----------+-------------+---------+---------------------------------------+

    """

    @staticmethod
    def help():
        print(StaticInput.__doc__)

    def __init__(self, channel: int = 0, board=None):
        self.sys_id = 0x50 | channel
        self._readonly = False

        self.current = {'id': self.sys_id << 8 | 0x00,
                        'type': float,
                        'unit': 'A',
                        'range': [-1, 1],
                        'default': 0.0,
                        'value': 0.0}
        InputStage.__init__(self, channel, board)
        self.name = self.__class__.__name__
        if not is_valid_channel(self._channel):
            raise ValueError('Channel Range Error')

    def SetCurrent(self, value):
        return self.set_register('current', value)

    def GetCurrent(self):
        return self.get_register('current')


class Analog(InputStage):
    r"""
Input Channel Systems - Analog Input
System ID: 0x58 through 0x5f

+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| Register Name  | Id   | Type        | Unit               | Range       | Default | Comment                |
+================+======+=============+====================+=============+=========+========================+
| unit           |0x01  | uint 32-bit | None               |0            | 0       | See registers table 1  |
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

    """

    @staticmethod
    def help():
        print(Analog.__doc__)

    def __init__(self, channel: int = 0, board=None):
        self.sys_id = 0x58 | channel
        self._readonly = False
        self._unitranges = {'A': [-1, 1]}

        self.unit = {'id': self.sys_id << 8 | 0x01,
                     'type': int,
                     'unit': ['A'],
                     'range': {0: 'Current'},
                     'default': 0,
                     'value': 0}
        self.minimum = {'id': self.sys_id << 8 | 0x02,
                        'type': float,
                        'unit': 'Volt',
                        'range': None,
                        'default': 0.0,
                        'value': 0.0}
        self.maximum = {'id': self.sys_id << 8 | 0x03,
                        'type': float,
                        'unit': 'Volt',
                        'range': None,
                        'default': 0.0,
                        'value': 0.0}
        self.mapping_minimum = {'id': self.sys_id << 8 | 0x04,
                                'type': float,
                                'unit': 'A',
                                'range': [-1, 1],
                                'default': 0,
                                'value': 0}
        self.mapping_maximum = {'id': self.sys_id << 8 | 0x05,
                                'type': float,
                                'unit': ['A', None, 'Degrees'],
                                'range': None,
                                'default': 0,
                                'value': 0}
        InputStage.__init__(self, channel, board)
        self.name = self.__class__.__name__
        if not is_valid_channel(self._channel):
            raise ValueError('Channel Range Error')

    def set_register(self, register_name_or_id: str or int, value):
        if self._board is not None:
            if isinstance(register_name_or_id, int):
                register_list = get_registers(self.__class__, self._channel)
                register_name_or_id = [item[0] for item in register_list if
                                       item[1]['id'] & 0x000f == register_name_or_id][0]
            response = self._board.set_value(self.__dict__[register_name_or_id], value)
            if isinstance(value, list):
                value = value[0]
            self.__dict__[register_name_or_id]['value'] = value
            if register_name_or_id == 'unit':
                self.mapping_minimum['unit'] = self.unit['unit'][value]
                self.mapping_minimum['range'] = self._unitranges[self.mapping_minimum['unit']]
                self.mapping_maximum['unit'] = self.unit['unit'][value]
                self.mapping_maximum['range'] = self._unitranges[self.mapping_minimum['unit']]
                return response
        return None

    def SetUnit(self, value):
        return self.set_register('unit', value)

    def GetUnit(self):
        return self.get_register('unit')

    def GetMinimum(self):
        return self.get_register('minimum')

    def GetMaximum(self):
        return self.get_register('maximum')

    def GetMappingMinimum(self):
        return self.get_register('mapping_minimum')

    def GetMappingMaximum(self):
        return self.get_register('mapping_maximum')


class SignalGenerator(InputStage):
    r"""
Input Channel Systems - Signal Generator Channel
System ID for channel 0: 0x60

+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| Register Name  | Id   | Type        | Unit               | Range       | Default | Comment                |
+================+======+=============+====================+=============+=========+========================+
| unit           | 0x00 | uint 32-bit | None               | 0           |   0     | See registers table 1  |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| run            | 0x01 | bool        | bool               | True / False|   0     |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| shape          | 0x02 | uint 32-bit |    None            | 0 to 3      |   0     | See registers table 2  |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| frequency      | 0x03 | float 32-bit|    Hz              |             |   0     |                        |
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
|external_trigger| 0x09 | uint 32-bit | None               | 0 to 2      | 0       | 0=disabled             |
|                |      |             |                    |             |         | 1=rising/falling edge  |
|                |      |             |                    |             |         | 2=rising edge          |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| output         | 0x0a |   float     |                    |             |         |                        |
+----------------+------+-------------+--------------------+-------------+---------+------------------------+


registers table 1:

+---------------+-------+
| Waveform Unit | Value |
+===============+=======+
| Current       | 0     |
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
        print(SignalGenerator.__doc__)

    def __init__(self, channel: int = 0, board=None, sys_id_base=0x60):
        self.name = self.__class__.__name__

        self.sys_id = sys_id_base | channel

        self.unit = {'id': self.sys_id << 8 | 0x00,
                     'type': int,
                     'unit': None,
                     'range': {0: 'Current'},
                     'default': 0,
                     'value': 0}
        self.run = {'id': self.sys_id << 8 | 0x01,
                    'type': int,
                    'unit': bool,
                    'range': [0, 1],
                    'default': 0,
                    'value': 0}
        self.shape = {'id': self.sys_id << 8 | 0x02,
                      'type': int,
                      'unit': None,
                      'range': {0: 'Sinusoidal', 1: 'Triangular', 2: 'Rectangular', 3: 'Sawtooth', 4: 'Pulse'},
                      'default': 0,
                      'value': 0}
        self.frequency = {'id': self.sys_id << 8 | 0x03,
                          'type': float,
                          'unit': 'Hz',
                          'range': None,
                          'default': 0.0,
                          'value': 0.0}
        self.amplitude = {'id': self.sys_id << 8 | 0x04,
                          'type': float,
                          'unit': None,
                          'range': None,
                          'default': 0.0,
                          'value': 0.0}
        self.offset = {'id': self.sys_id << 8 | 0x05,
                       'type': float,
                       'unit': None,
                       'range': None,
                       'default': 0.0,
                       'value': 0.0}
        self.phase = {'id': self.sys_id << 8 | 0x06,
                      'type': float,
                      'unit': 'Degrees',
                      'range': [0, 360],
                      'default': 0.0,
                      'value': 0.0}
        self.cycles = {'id': self.sys_id << 8 | 0x07,
                       'type': int,
                       'unit': None,
                       'range': None,
                       'default': -1,
                       'value': -1}
        self.duty_cycle = {'id': self.sys_id << 8 | 0x08,
                           'type': float,
                           'unit': None,
                           'range': [0, 1.0],
                           'default': 0.5,
                           'value': 0.5}
        self.external_trigger = {'id': self.sys_id << 8 | 0x09,
                       'type': int,
                       'unit': None,
                       'range': None,
                       'default': False,
                       'value': False}
        self.output = {'id': self.sys_id << 8 | 0x0a,
                               'type': float,
                               'unit': None,
                               'range': None,
                               'default': None,
                               'value': None}
        InputStage.__init__(self, channel, board)
        if not is_valid_channel(self._channel):
            raise ValueError('Channel Range Error')

    def SetUnit(self, value):
        return self.set_register('unit', value)

    def GetUnit(self):
        return UnitType(self.get_register('unit'))

    def Run(self):
        return self.set_register('run', 1)

    def Stop(self):
        return self.set_register('run', 0)

    def GetRunningStatus(self):
        return self.get_register('run')

    def SetShape(self, value):
        return self.set_register('shape', value)

    def GetShape(self):
        return self.get_register('shape')

    def SetFrequency(self, value):
        return self.set_register('frequency', value)

    def GetFrequency(self):
        return self.get_register('frequency')

    def SetAmplitude(self, value):
        return self.set_register('amplitude', value)

    def GetAmplitude(self):
        return self.get_register('amplitude')

    def SetOffset(self, value):
        return self.set_register('offset', value)

    def GetOffset(self):
        return self.get_register('offset')

    def SetPhase(self, value):
        return self.set_register('phase', value)

    def GetPhase(self):
        return self.get_register('phase')

    def SetCycles(self, value):
        return self.set_register('cycles', value)

    def GetCycles(self):
        return self.get_register('cycles')

    def SetDutyCycle(self, value):
        return self.set_register('duty_cycle', value)

    def GetDutyCycle(self):
        return self.get_register('duty_cycle')

    def SetExternalTrigger(self, value):
        return self.set_register('external_trigger', value)

    def GetOutput(self):
        return self.get_register('output')


class VectorPatternUnit(InputStage):
    r"""
Input Channel Systems - Vector Pattern Unit
System ID: 0x68 through 0x6f

+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| Register Name  | Id   | Type        | Unit               | Range       | Default | Comment                |
+================+======+=============+====================+=============+=========+========================+
|unit            | 0x00 | uint 32-bit | None               | 0           | 0       | See registers table    |
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

    """

    @staticmethod
    def help():
        print(VectorPatternUnit.__doc__)

    def __init__(self, channel: int = 0, board=None, sys_id_base=0x68):
        self.sys_id = sys_id_base | channel

        self.unit = {'id': self.sys_id << 8 | 0x00,
                     'type': int,
                     'unit': None,
                     'range': {0: 'Current'},
                     'default': 1,
                     'value': 1}
        self.run = {'id': self.sys_id << 8 | 0x01,
                    'type': bool,
                    'unit': None,
                    'range': [True, False],
                    'default': False,
                    'value': False}
        self.start = {'id': self.sys_id << 8 | 0x02,
                      'type': int,
                      'unit': None,
                      'range': None,
                      'default': 0,
                      'value': 0}
        self.end = {'id': self.sys_id << 8 | 0x03,
                    'type': int,
                    'unit': None,
                    'range': None,
                    'default': 0,
                    'value': 0}
        self.frequency_speed = {'id': self.sys_id << 8 | 0x04,
                                'type': float,
                                'unit': 'Hz',
                                'range': None,
                                'default': 10000,
                                'value': 10000}
        self.min_speed = {'id': self.sys_id << 8 | 0x05,
                          'type': float,
                          'unit': 'Hz',
                          'range': None,
                          'default': 0,
                          'value': 0.0}
        self.max_speed = {'id': self.sys_id << 8 | 0x06,
                          'type': float,
                          'unit': 'Hz',
                          'range': None,
                          'default': 0,
                          'value': 0.0}
        self.cycles = {'id': self.sys_id << 8 | 0x07,
                       'type': int,
                       'unit': 'Hz',
                       'range': None,
                       'default': -1,
                       'value': -1}
        self.external_trigger = {'id': self.sys_id << 8 | 0x08,
                       'type': int,
                       'unit': None,
                       'range': None,
                       'default': False,
                       'value': False}
        self.output = {'id': self.sys_id << 8 | 0x09,
                               'type': float,
                               'unit': None,
                               'range': None,
                               'default': None,
                               'value': None}
        self.index = {'id': self.sys_id << 8 | 0x0a,
                      'type': int,
                      'unit': None,
                      'range': None,
                      'default': 0,
                      'value': 0}

        InputStage.__init__(self, channel, board)
        self.name = self.__class__.__name__
        if not is_valid_channel(self._channel):
            raise ValueError('Channel Range Error')

    def SetUnit(self, value):
        return self.set_register('unit', value)

    def GetUnit(self):
        return self.get_register('unit')

    def Run(self):
        return self.set_register('run', 1)

    def Stop(self):
        return self.set_register('run', 0)

    def GetRunningStatus(self):
        return self.get_register('run')

    def SetStart(self, value):
        return self.set_register('start', value)

    def GetStart(self):
        return self.get_register('start')

    def SetEnd(self, value):
        return self.set_register('end', value)

    def GetEnd(self):
        return self.get_register('end')

    def SetFreqSampleSpeed(self, value):
        return self.set_register('frequency_speed', value)

    def GetFreqSampleSpeed(self):
        return self.get_register('frequency_speed')

    def GetMinFreqSampleSpeed(self):
        return self.get_register('min_speed')

    def GetMaxFreqSampleSpeed(self):
        return self.get_register('max_speed')

    def SetCycles(self, value):
        return self.set_register('cycles', value)

    def GetCycles(self):
        return self.get_register('cycles')

    def GetIndex(self):
        return self.get_register('index')

    def SetExternalTrigger(self, value):
        if type(value) == bool:
            value = int(value)
        return self.set_register('external_trigger', value)

    def GetOutput(self):
        return self.get_register('output')


class QuadrantVectorPatternUnit(InputStage):
    r"""

 * Quadrant vector pattern system ID base: 0x80
 *
 * | Address | Name                    | Default | Description                                                                              | Format and value |
 * | ------- | ----------------------- | ------- | ---------------------------------------------------------------------------------------- | ---------------- |
 * | 0       | unit type               | 0       | see ChannelValue                                                                         | uint32           |
 * | 1       | run                     | false   | turn system on and off                                                                   | boolean          |
 * | 2       | quadrant vector 1 start | 0       | index in Vector Pattern Memory of first point of vector to move to quadrant position 1   | uint32           |
 * | 3       | quadrant vector 1 end   | 0       | index in Vector Pattern Memory after last point of vector to move to quadrant position 1 | uint32           |
 * | 4       | quadrant vector 2 start | 0       | index in Vector Pattern Memory of first point of vector to move to quadrant position 2   | uint32           |
 * | 5       | quadrant vector 2 end   | 0       | index in Vector Pattern Memory after last point of vector to move to quadrant position 2 | uint32           |
 * | 6       | quadrant vector 3 start | 0       | index in Vector Pattern Memory of first point of vector to move to quadrant position 3   | uint32           |
 * | 7       | quadrant vector 3 end   | 0       | index in Vector Pattern Memory after last point of vector to move to quadrant position 3 | uint32           |
 * | 8       | quadrant vector 4 start | 0       | index in Vector Pattern Memory of first point of vector to move to quadrant position 4   | uint32           |
 * | 9       | quadrant vector 4 end   | 0       | index in Vector Pattern Memory after last point of vector to move to quadrant position 4 | uint32           |
 */

    """

    @staticmethod
    def help():
        print(QuadrantVectorPatternUnit.__doc__)

    def __init__(self, channel: int = 0, board=None):
        self.sys_id = 0x80 | channel

        self.unit = {'id': self.sys_id << 8 | 0x00,
                     'type': int,
                     'unit': None,
                     'range': {0: 'Current', 1: 'OF', 2: 'XY'},
                     'default': 1,
                     'value': 1}
        self.run = {'id': self.sys_id << 8 | 0x01,
                    'type': bool,
                    'unit': None,
                    'range': [True, False],
                    'default': False,
                    'value': False}
        self.startQ1 = {'id': self.sys_id << 8 | 0x02,
                      'type': int,
                      'unit': None,
                      'range': None,
                      'default': 0,
                      'value': 0}
        self.endQ1 = {'id': self.sys_id << 8 | 0x03,
                    'type': int,
                    'unit': None,
                    'range': None,
                    'default': 0,
                    'value': 0}
        self.startQ2 = {'id': self.sys_id << 8 | 0x04,
                      'type': int,
                      'unit': None,
                      'range': None,
                      'default': 0,
                      'value': 0}
        self.endQ2 = {'id': self.sys_id << 8 | 0x05,
                    'type': int,
                    'unit': None,
                    'range': None,
                    'default': 0,
                    'value': 0}
        self.startQ3 = {'id': self.sys_id << 8 | 0x06,
                      'type': int,
                      'unit': None,
                      'range': None,
                      'default': 0,
                      'value': 0}
        self.endQ3 = {'id': self.sys_id << 8 | 0x07,
                    'type': int,
                    'unit': None,
                    'range': None,
                    'default': 0,
                    'value': 0}
        self.startQ4 = {'id': self.sys_id << 8 | 0x08,
                      'type': int,
                      'unit': None,
                      'range': None,
                      'default': 0,
                      'value': 0}
        self.endQ4 = {'id': self.sys_id << 8 | 0x09,
                    'type': int,
                    'unit': None,
                    'range': None,
                    'default': 0,
                    'value': 0}

        InputStage.__init__(self, channel, board)
        self.name = self.__class__.__name__
        if not is_valid_channel(self._channel):
            raise ValueError('Channel Range Error')

    def SetUnit(self, value):
        return self.set_register('unit', value)

    def GetUnit(self):
        return self.get_register('unit')

    def Run(self):
        return self.set_register('run', 1)

    def Stop(self):
        return self.set_register('run', 0)

    def GetRunningStatus(self):
        return self.get_register('run')

    def SetStartQ1(self, value):
        return self.set_register('startQ1', value)

    def GetStartQ1(self):
        return self.get_register('startQ1')

    def SetEndQ1(self, value):
        return self.set_register('endQ1', value)

    def GetEndQ1(self):
        return self.get_register('endQ1')

    def SetStartQ2(self, value):
        return self.set_register('startQ2', value)

    def GetStartQ2(self):
        return self.get_register('startQ2')

    def SetEndQ2(self, value):
        return self.set_register('endQ2', value)

    def GetEndQ2(self):
        return self.get_register('endQ2')

    def SetStartQ3(self, value):
        return self.set_register('startQ3', value)

    def GetStartQ3(self):
        return self.get_register('startQ3')

    def SetEndQ3(self, value):
        return self.set_register('endQ3', value)

    def GetEndQ3(self):
        return self.get_register('endQ3')

    def SetStartQ4(self, value):
        return self.set_register('startQ4', value)

    def GetStartQ4(self):
        return self.get_register('startQ4')

    def SetEndQ4(self, value):
        return self.set_register('endQ4', value)

    def GetEndQ4(self):
        return self.get_register('endQ4')



class RasterScan(InputStage):
    r"""
Input Channel Systems - Raster Scan
System ID: 0x70 through 0x77

+------------------+------+-------------+---------+--------------+---------+--------------------------------+
| Register Name    | Id   | Type        | Unit    | Range        | Default | Comment                        |
+==================+======+=============+=========+==============+=========+================================+
| run              | 0x01 | uint 32-bit | bool    | True / False | 0       |                                |
+------------------+------+-------------+---------+--------------+---------+--------------------------------+
|number_of_lines   | 0x02 | uint 32-bit | None    |              |         |                                |
+------------------+------+-------------+---------+--------------+---------+--------------------------------+
|slow_axis_range   | 0x03 | float 32-bit| Degrees |              |         |                                |
+------------------+------+-------------+---------+--------------+---------+--------------------------------+
|fast_axis_range   | 0x04 | float 32-bit| Degrees |              |         |                                |
+------------------+------+-------------+---------+--------------+---------+--------------------------------+
|orientation       | 0x05 | uint 32-bit | None    | [0, 1]       | 0       | 0 – horizontal, 1 – vertical   |
+------------------+------+-------------+---------+--------------+---------+--------------------------------+
|frequency         | 0x06 | float 32-bit| Hz      |              |         |                                |
+------------------+------+-------------+---------+--------------+---------+--------------------------------+

    """

    # TODO: Not implemented yet in firmware
    @staticmethod
    def help():
        print(RasterScan.__doc__)

    def __init__(self, channel: int = 0, board=None):
        self.sys_id = 0x70 | channel
        self._readonly = False

        self.unit = {'id': self.sys_id << 8 | 0x00,
                     'type': int,
                     'unit': None,
                     'range': {0: 'Current', 1: 'OF', 2: 'XY'},
                     'default': 1,
                     'value': 1}
        self.run = {'id': self.sys_id << 8 | 0x01,
                    'type': bool,
                    'unit': None,
                    'range': [True, False],
                    'default': 0,
                    'value': 0.0}
        self.number_of_lines = {'id': self.sys_id << 8 | 0x02,
                                'type': int,
                                'unit': None,
                                'range': [0, 2],
                                'default': 0,
                                'value': 0.0}
        self.slow_axis_range = {'id': self.sys_id << 8 | 0x03,
                                'type': float,
                                'unit': 'Degree',
                                'range': [0, 2],
                                'default': 0,
                                'value': 0.0}
        self.fast_axis_range = {'id': self.sys_id << 8 | 0x04,
                                'type': float,
                                'unit': 'Degree',
                                'range': [0, 2],
                                'default': 0,
                                'value': 0.0}
        self.orientation = {'id': self.sys_id << 8 | 0x05,
                            'type': bool,
                            'unit': None,
                            'range': {0: 'Horizontal', 1: 'Vertical'},
                            'default': 0,
                            'value': 0.0}
        self.frequency = {'id': self.sys_id << 8 | 0x06,
                          'type': float,
                          'unit': 'Hz',
                          'range': None,
                          'default': 0,
                          'value': 0.0}
        InputStage.__init__(self, channel, board)
        self.name = self.__class__.__name__
        if not is_valid_channel(self._channel):
            raise ValueError('Channel Range Error')


class FlowerPattern(InputStage):
    r"""
Input Channel Systems - Flower Pattern
System ID: 0x78 through 0x7f

+----------------+------+-------------+--------------------+-------------+---------+------------------------+
| Register Name  | Id   | Type        | Unit               | Range       | Default | Comment                |
+================+======+=============+====================+=============+=========+========================+


    """

    # TODO: Not implemented yet in firmware
    @staticmethod
    def help():
        print(FlowerPattern.__doc__)

    def __init__(self, channel: int = 0, board=None):
        self.sys_id = 0x70 | channel
        self._readonly = False

        self.PLACEHOLDER = {'id': self.sys_id << 8 | 0x00,
                            'type': float,
                            'unit': 'Hz',
                            'range': None,
                            'default': 0,
                            'value': 0}
        self.unit = {'id': self.sys_id << 8 | 0x00,
                     'type': int,
                     'unit': None,
                     'range': {0: 'Current', 1: 'OF', 2: 'XY'},
                     'default': 1,
                     'value': 1}
        InputStage.__init__(self, channel, board)
        self.name = self.__class__.__name__
        if not is_valid_channel(self._channel):
            raise ValueError('Channel Range Error')