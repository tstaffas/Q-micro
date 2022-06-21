from lens import Lens
import time
import numpy as np

lens = Lens('COM4', debug=False)  # set debug to True to see a serial communication log, make sure the COM is right, otherwise it crashes
print(lens.firmware_type)
print(lens.firmware_version)
print(lens.get_firmware_branch())
print('Lens serial number:', lens.lens_serial)
print('Lens temperature:', lens.get_temperature())

# focal power mode example
min_fp, max_fp = lens.to_focal_power_mode()
print('Minimal diopter:', min_fp)
print('Maximum diopter:', max_fp)
print(lens.set_temperature_limits(20,45 ))

diopter = np.linspace(-9.0,9.0,100) # these parameters can be varied --> changes the scanning range (from -10D to 10D possible)

"""for a in diopter:
    lens.set_diopter(a)
    time.sleep(0.1)"""

lens.set_diopter(+4)

# current mode example
#lens.to_current_mode()
#lens.set_current(100)
