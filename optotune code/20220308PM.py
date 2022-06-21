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
sg_1.SetAmplitude(0.100)
sg_1.SetFrequency(20)                                    

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

startpos = -0.01   # max value is 0.7   
endpos = 0.01       
stepnumber = 10

stepsize = (endpos - startpos)/stepnumber

amp = np.linspace(startpos,endpos,stepnumber)
sg_1.Run()

for a in amp:                                         
    #print("a=",a)
    sg_0.SetCurrent(a)
    start_time = time.time()
    seconds = 0.05
    while a < endpos:
        current_time = time.time()
        elapsed_time = current_time - start_time
        if elapsed_time > seconds:
            #print("Finished iterating in: " + str(int(elapsed_time))  + " seconds")
            break
        
sg_1.SetAmplitude(0)
sg_0.SetCurrent(0) 
