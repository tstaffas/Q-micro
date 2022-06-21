import optoMDC
import time
import numpy as np 
mre2 = optoMDC.connect()
mre2.set_value(0xC014, float(200)) # lower the cutoff frequency for the low pass filter that affects derivative control action

ch_0 = mre2.Mirror.Channel_0

#ch_0.SignalGenerator.SetAsInput()                   # (1) here we tell the Manager that the sig gen is the desired input on channel 0
si_0 = mre2.Mirror.Channel_0.StaticInput
#ch_0.StaticInput.SetAsInput()                        # (1) here we tell the Manager that we will use a static input on channel 0

ch_0.InputConditioning.SetGain(1.0)                  # (2) here we tell the Manager some input conditioning parameters
ch_0.SetControlMode(optoMDC.Units.CURRENT)           # (3) here we tell the Manager that our input will be in units of current
ch_0.LinearOutput.SetCurrentLimit(0.7)               # (4) here we tell the Manager to limit the current to 700mA (default)

ch_0.Manager.CheckSignalFlow()

sg_0 = mre2.Mirror.Channel_0.SignalGenerator

sg_0.SetUnit(optoMDC.Units.CURRENT)                 # here we set the sig gen to output in units of current (This must match the control mode!)
sg_0.SetShape(optoMDC.Waveforms.SINUSOIDAL)         # here we set the sig gen output waveform type
sg_0.SetFrequency(0.1)                              # here we set the frequency in Hz (1 Hz --> 1 s)
sg_0.SetAmplitude(0.100)                            # here we set the amplitude in Amps
sg_0.Run()

ch_0.Manager.CheckSignalFlow()  




ch_1 = mre2.Mirror.Channel_1

ch_1.SignalGenerator.SetAsInput()                    # (1) here we tell the Manager that the sig gen is the desired input
ch_1.InputConditioning.SetGain(1.0)                  # (2) here we tell the Manager some input conditioning parameters
ch_1.SetControlMode(optoMDC.Units.CURRENT)           # (3) here we tell the Manager that our input will be in units of current
ch_1.LinearOutput.SetCurrentLimit(0.7)               # (4) here we tell the Manager to limit the current to 700mA (default)

ch_1.Manager.CheckSignalFlow()

sg_1 = mre2.Mirror.Channel_1.SignalGenerator

sg_1.SetUnit(optoMDC.Units.CURRENT)                 # here we set the sig gen to output in units of current (This must match the control mode!)
sg_1.SetShape(optoMDC.Waveforms.SINUSOIDAL)         # here we set the sig gen output waveform type
sg_1.SetFrequency(1.0)                              # here we set the frequency in Hz (1 Hz --> 1 s)
sg_1.SetAmplitude(0.100)                            # here we set the amplitude in Amps
#sg_1.Run()

#sg_1.SetAmplitude(0)
#sg_0.SetAmplitude(0)


"""Below is a timed loop of 1 second for different currents"""





startpos = -0.6
endpos = 0.6
stepnumber = 10
stepsize = (endpos - startpos)/stepnumber

amp = np.linspace(startpos,endpos,stepnumber)

for a in amp:                                         
    position = si_0.SetCurrent(a)
    print("a=",a)
    start_time = time.time()
    seconds = 1
    while True:                                    
        current_time = time.time()
        elapsed_time = current_time - start_time
        sg_1.Run()
        if elapsed_time > seconds:
            print("Finished iterating in: " + str(int(elapsed_time))  + " seconds")
            break


     
sg_1.SetAmplitude(0)
sg_0.SetAmplitude(0)     











