import optoMDC
import time
import numpy as np 
mre2 = optoMDC.connect()
mre2.set_value(0xC014, float(200)) # lower the cutoff frequency for the low pass filter that affects derivative control action

"""Setting up channel 1 - Sinusoid"""

ch_1 = mre2.Mirror.Channel_1

ch_1.InputConditioning.SetGain(1.0)                 
ch_1.SetControlMode(optoMDC.Units.CURRENT)
ch_1.LinearOutput.SetCurrentLimit(0.7)               

sg_1 = mre2.Mirror.Channel_1.SignalGenerator
sg_1.SetUnit(optoMDC.Units.CURRENT)                 
sg_1.SetShape(optoMDC.Waveforms.SINUSOIDAL)         
sg_1.SetAmplitude(0.06)
sg_1.SetFrequency(1)   # change                                 

ch_1.Manager.CheckSignalFlow()

"""Setting up channel 0 - DC"""

ch_0 = mre2.Mirror.Channel_0

ch_0.SignalGenerator.SetAsInput()                   
ch_0.StaticInput.SetAsInput()
ch_0.InputConditioning.SetGain(1.0)                  
ch_0.SetControlMode(optoMDC.Units.CURRENT)           
ch_0.LinearOutput.SetCurrentLimit(0.7)               

ch_0.Manager.CheckSignalFlow()

sg_0 = mre2.Mirror.Channel_0.SignalGenerator
sg_0 = mre2.Mirror.Channel_0.StaticInput

"""Change the 3 parameters below to fit with the system"""

"""startpos = 0.01 # max value is 0.7   
endpos = 0.014
stepnumber = 10"""

startpos = 0.01 # max value is 0.7   
endpos = 0.016
stepnumber = 10

stepsize = (endpos - startpos)/stepnumber

amp = np.linspace(startpos,endpos,stepnumber)
sg_1.Run()

for a in amp:                                         
    sg_0.SetCurrent(a)
    start_time = time.time()
    seconds = 2 # change
    while a < endpos:
        current_time = time.time()
        elapsed_time = current_time - start_time
        if elapsed_time > seconds:
            break
sg_0.SetCurrent(0) 
time.sleep(3)
sg_1.SetAmplitude(0)

