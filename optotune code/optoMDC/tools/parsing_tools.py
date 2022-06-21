from optoKummenberg.tools.parsing_tools import *


def parse_error_flags_mre2(error_flag_data: int):
    r"""
    Parses error flag register values. Given error number, returns error string.

    Parameters
    ----------
    error_flag_data : int
        Error code hex number, will convert if string.

    Returns
    -------
    code: str
        Error code dictionary.
    """
    bits = format(error_flag_data[0], '#032b')[2::]
    error_result = {
        'Proxy Disconnected': bool(int(bits[29])),
        'Proxy Temperature Threshold Reached': bool(int(bits[28])),
        'Mirror Temperature Threshold Reached': bool(int(bits[27])),
        'Mirror EEPROM Invalid': bool(int(bits[26])),
        'Mirror Unstable': bool(int(bits[25])),
        'Linear Output Limit Reached': bool(int(bits[24])),
        'Linear Output Average Limit Reached': bool(int(bits[23])),
        'XY Input Trimmed': bool(int(bits[22])),
        'Proxy Was Disconnected': bool(int(bits[21])),
        'Proxy Temperature Threshold Was Reached': bool(int(bits[20])),
        'Mirror Temperature Threshold Was Reached': bool(int(bits[19])),
        'Linear Output Limit Was Reached': bool(int(bits[18])),
        'Linear Output Average Limit Was Reached': bool(int(bits[17])),
        'XY Input Was Trimmed': bool(int(bits[16])),
        'Reserved': bits[0:16]
    }

    return error_result
