"""

 DfuSeCommand.exe [options] [Agrument][[options] [Agrument]...]

  -?                   (Show this help)
  -c                   (Connect to a DFU device )
     --de  device      : Number of the device target, by default 0
     --al  target      : Number of the alternate target, by default 0
  -u                   (Upload flash contents to a .dfu file )
     --fn  file_name   : full path name of the file
  -d                   (Download the content of a file into MCU flash)
     --v               : verify after download
     --o               : optimize; removes FFs data
     --fn  file_name   : full path name (.dfu file)
"""
import subprocess
import os
from enum import Enum

current_working_dir = os.getcwd()
root_tools_path = "src/main/python/optoMDC/tools"
fw_update_path = "dfusecommand.exe"
update_option_path = "SwitchBackFromDFU.dfu"
dfu_extension = '.dfu'

# TODO: get dfu file path somehow. for now, just type it into update_firmware param


def update_firmware(file_path: str = ''):
    if file_path == '':
        exit_code = UpdateStatus.FilePathMissingError.value
    if not check_if_file_exists(file_path):
        print(UpdateStatus.FileNotFoundError.value.format(file_path))
        exit_code = UpdateStatus.FileNotFoundError.value.format(file_path)
    if not is_device_in_dfu():
        print(UpdateStatus.NoDfuDevice.value)
        exit_code = UpdateStatus.NoDfuDevice.value
    else:
        exit_code = process_update(file_path)
        get_device_from_dfu_mode()
    return analyze_exit_code(exit_code)


def check_if_file_exists(file_path):
    # TODO: return true if file exists
    return True


def is_device_in_dfu():
    # TODO: parse response from batch script output of 'UpdateOperations.GetDfuDevices' options
    # get number of devices, read line by line, parse to get device names, check if this device in list, return bool
    result = subprocess.run([fw_update_path, UpdateOperations.GetDfuDevices.value])
    input('Press To Continue...')
    return result


def process_update(file_path):
    # TODO: does import sys include Process. if not, do manually.
    #  response from batch script output of 'UpdateOperations.UpdateFirmware' options

    # TODO: return exit codes from result
    return 0


def get_device_from_dfu_mode():
    # TODO: parse response from batch script output of 'UpdateOperations.GetDfuDevices' options
    pass


def analyze_exit_code(exit_code):
    # TODO: maybe not exit the interpreter...
    if exit_code == UpdateStatus.UpdateSuccess:
        exit(0)
    else:
        exit(1)


class UpdateOperations(Enum):
    UpdateFirmware = " -c --al 0 -d --v --fn " + fw_update_path
    GetBackFromDfu = " -c --al 1 -d --v --fn " + update_option_path
    GetDfuDevices = " -c --de"


class UpdateStatus(Enum):
    UpdateError = 'Error: Update Not Successful.'  # TODO: are there params from the batch output useful to failure?
    NoDfuDevice = 'Error: This Device Is Not In DFU List.'  # TODO: list dfu devices and this device?
    UpdateSuccess = 'Update Successful.'  # TODO: Add FW information?
    FileNotFoundError = 'Error: File Not Found - [{}]'
    FilePathMissingError = 'Error: File Path Missing.'


if __name__ == '__main__':
    print('Input DFU File Path.')
    file_path = input('>>>')
    update_firmware(file_path=file_path)