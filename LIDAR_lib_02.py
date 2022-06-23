#Packages used for analysis
import numpy as np
from pathlib import Path
import os

from numpy import inf
import scipy.signal
import time as t
from scipy.signal import chirp, find_peaks, peak_widths
from scipy.optimize import curve_fit

#Packages used for curve fitting
import lmfit as lm
from lmfit.models import GaussianModel, ConstantModel, SkewedGaussianModel
from lmfit import Parameters

#Packages used for plotting
import matplotlib.pyplot as plt
from colour import Color
from matplotlib import cm
import matplotlib.cm as cmx
from mpl_toolkits.mplot3d import Axes3D

import random
import warnings
warnings.simplefilter('ignore', np.RankWarning)

#------- Functions to calculate 3D data ----------
def calcDistance(t_ref,t_signal):
    #calculates the distance between times, times are given in picoseconds and result is given in mm
    return 1000*0.5*(t_signal-t_ref)*(10**(-12))*299792458

def getDistance(ref_peak, histogram, binsize = 16):
    #Returns the distance between the highest peak in the histogram and a reference value that is measured seperatly.
    return calcDistance(binsize*ref_peak, binsize*np.where(histogram == np.amax(histogram))[0][0])
   
def XYZ(r,thetaX,thetaY):
    #converts the distance data and angle information to cartesian coordinates
    #(My version)
    
    z = r/(np.sqrt(1+np.tan(thetaX)**2+np.tan(thetaY)**2))
    y = z*np.tan(thetaY)
    x = z*np.tan(thetaX)

    """
    #Spherical
    z = r*np.cos(thetaY)*np.cos(thetaX)
    y = r*np.sin(thetaY)
    x = r*np.cos(thetaY)*np.sin(thetaX)
    """
    return x,y,z
    
def angles(rect,dimX,dimY):
    #rect = [x_max,y_max, x_min, y_min]
    #Calculates the angles of the mirrors as a function of the supplied x_voltages  (Should depend on the initial position, should be checked)

    x_voltages = np.linspace(int(float(rect[0])),int(float(rect[2])),dimX)
    y_voltages = np.linspace(int(float(rect[1])),int(float(rect[3])),dimY)
    
    x_deg = x_voltages * 2.5 * np.pi / 180   
    y_deg = y_voltages * 2.5 * np.pi / 180 #OBS: minus sign on y might be a relic/pr needed. Check images against reality

    return x_deg, y_deg

#------- Functions for plotting and saving data ------- 
def scatter(d_data, file, cutoff, name = "",save = True, show = False, **kwargs):
    #Produces a 3d scatterplot of the generated data and saves it
    Xdata , Ydata, Zdata, order  = [], [], [], []
    for p in d_data:
        v = d_data[p]
        if  v[3]==1:
            Xdata.append(v[0])
            Ydata.append(v[1])
            Zdata.append(v[2])
            
        
    fig = plt.figure(figsize=(15,15))
    ax = fig.add_subplot(111,projection="3d")

    #### Colour scheme ##### Some nice colour gradients to use
    C = {"#4568DC" : "#B06AB3"#(blue to purple)  
        ,"#C33764" : "#1D2671" #(pink to blue)
        ,"#00F260" : "#0575E6" #(green to blue) 
        ,"#bc4e9c" : "#f80759" #(purple to pink)
        ,"#333333" : "#dd1818" # (dark to red) 
        ,"#009FFF" : "#ec2F4B" #(blue to red)
        ,"#654ea3" : "#eaafc8" #(ultraviolet)
        ,"#a8ff78" : "#78ffd6" #can't remember)
        ,"#005AA7" : "#FFFDE4" #(blue to white)
        ,"#0bf91f" : "#ff002c" #(green to red)
        }
    
    """
    Code block assigns a color to every point. No real information is stored in this color, it simply makes the images nicer and easier to read
    """
    r = len(Zdata)
    key = random.choice(list(C.keys())) #A random choice of gradient is possible
    key = "#0bf91f"  #I found a colour gradient I like best
    primer = Color(key)
    base = Color(C[key])
    colors = list(primer.range_to(base, r ))
    
    zmin = np.min(Zdata)
    zmax = np.max(Zdata)

    zcol =  [ np.round((i-zmin)/(zmax-zmin)*r-1) for i in Zdata ]
    col = []

    for num in zcol:
        col += [colors[int(num)].rgb]
    
    ##### Cleaning some of the data to avoid squished plots ####
    avg = np.mean([i for i in Zdata if not np.isnan(i)])
    std = np.std([i for i in Zdata if not np.isnan(i)])

    Zdata = [i if i > avg-cutoff*std and i < avg+cutoff*std else np.NaN for i in Zdata ]
    #Value of cutoff is asigned in ETA frontend because I was annoyed of digging through the code to change it all the time
    
    ax.scatter(Ydata,Zdata,Xdata, c = col ,s=1.5) #Plots the data
    try:
        
        ax.azim = int(kwargs['z_rot']) #sets a rototion of the plot if needed, not used much
        ax.elev = int(kwargs['x_rot'])
    except KeyError:
        pass
    
    try:
        ax.set_xlim(kwargs['xlim'])
    except KeyError:
        pass

    try:
        ax.set_ylim(kwargs['ylim'])
    except KeyError:
        pass
    
    try:
        ax.set_zlim(kwargs['zlim'])
    except KeyError:
        pass    
    
    #ax.set_title("3D reconstruction", fontsize = 40)
    ax.set_xlabel(" [mm]", fontsize = 40, labelpad=40)
    ax.set_ylabel(" [mm]", fontsize = 40, labelpad=40)
    ax.set_zlabel(" [mm]", fontsize = 40, labelpad=40)
    
    ax.tick_params(labelsize=30)
    
    #Saves the data
    if save: #Do you want to save the picture?
        if not os.path.exists(file.parent.joinpath(f'analyzed_images')): #If folder does not exist, create it
            os.makedirs(file.parent.joinpath(f'analyzed_images'))
        
        #Code block generates a new name for the image in order to not save over old results        
        folder = str(file.parent.joinpath(f'analyzed_images'))
        filename = name+file.stem+'_3Dplot.png'
        directory = os.fsencode(folder)
        FILES = [os.fsdecode(f) for f in os.listdir(directory)]
        i = 2
        while str(filename) in FILES:
            filename = name+file.stem+'_3Dplot_' +str(i)+  '.png'
            i+=1
            
        
        savepath = file.parent.joinpath(f'analyzed_images', filename)
        fig.savefig(savepath) # needs path

    if show == True:
        plt.show()
    plt.close('all')

 
def save_pixel(histogram,file,x,y, binsize):
    #Saves a single pixel (x,y), used mainly for trouble shooting and diagnosing
    if not os.path.exists(file.parent.joinpath(f'analyzed pixels')):
        os.makedirs(file.parent.joinpath(f'analyzed pixels'))
    
    savepath = file.parent.joinpath(f'analyzed pixels', f'pixel_x={x}_y={y}.txt')
    np.savetxt(savepath,np.transpose([np.arange(0,histogram[y][x].size)*binsize,histogram[y][x]]))

def save_pixel_array(histogram,file, dimX, dimY, binsize = 16):
    #Saves several pixels for diagnosing and trouble shooting the algorithm
    for i in range (9):
        x = random.randint(0,dimX-1)
        y = random.randint(0,dimY-1)
        
        save_pixel(histogram,file,x,y, binsize)

def save_all_pixels(histogram,file, dimX, dimY, binsize = 16):
    for i in range(dimX):
        for j in range(dimY):
            save_pixel(histogram, file, i,j , binsize)
    
def save_data(d_data, file, name):
    #Saves the X,Y,Z data in a text file

    x,y,z,valid, I, J  = [], [], [], [], [], []
    for p in d_data:
        v = d_data[p]
        x.append(v[0])
        y.append(v[1])
        z.append(v[2])
        valid.append(v[3])
        I.append(p[0])
        J.append(p[1])

    
    #return x,y,z,I,J

    #Saves the data
    if not os.path.exists(file.parent.joinpath(f'3d data')): #If folder does not exist, create it
        os.makedirs(file.parent.joinpath(f'3d data'))
    
    filename = name+file.stem
    savepath = file.parent.joinpath(f'3d data', filename + '.txt')
    np.savetxt(savepath,np.transpose([I,J,x,y,z, valid]), header = 'i,j,x,y,z,valid')

def save_intensity_data(d_data, i_data, file, name):
    
    x, y, z, I = [], [], [], []
    for p in d_data:
        x.append(p[0])
        y.append(p[1])
        z.append(d_data[p])
        I.append(i_data[p])

    #Saves the data
    if not os.path.exists(file.parent.joinpath(f'3d+intensity data')): #If folder does not exist, create it
        os.makedirs(file.parent.joinpath(f'3d+intensity data'))
    
    filename = name+file.stem
    savepath = file.parent.joinpath(f'3d+intensity data', filename + '.txt')
    np.savetxt(savepath,np.transpose([x,y,z,I]))

#-------  Functions to extract intensity -------
def integral(y, peak_value):
    peak_index = np.where(y == peak_value)[0][0]
    n = 10
    
    s = 0
    for j in range(peak_index-n, peak_index+n):
        try:
            s+=y[j]
            
        except IndexError:
            print("Integral failed: Maybe check this out")
            break
        
    return s

def integrate(y, i1, i2):
    return np.sum(y[i1:i2])

def find_percentiles(y, peak_index, peak_div = [2]):
    peak = y[peak_index]
    thresholds = [peak*div for div in peak_div]

    upper_index = []
    lower_index = []

    for t in thresholds:
        i = 1
        run_up, run_down = True, True
        while run_up or run_down:
            try:
                U = y[peak_index+i]
                L = y[peak_index-i]

                if U <= t and run_up:
                    upper_index.append(peak_index+i)
                    run_up = False

                if L <= t and run_down:
                    lower_index.append(peak_index-i)
                    run_down = False

                i+=1

            except IndexError:
                print('Failed to find percentile')
                break
    
    return upper_index, lower_index


#-------  Functions to fit plots to data -------
def peak_distance(x,y,index_ref):
    binsize = x[1]-x[0]
    #Returns the distance between the highest peak in the histogram and a reference value that is measured seperatly.
    height = np.amax(y)
    intensity = integral(y, height)
    
    return calcDistance(binsize*index_ref, binsize*np.where(y == height)[0][0]), intensity, height

def FWHM(y, peak_index, binsize):
    peak = y[peak_index]
    half_peak = peak/2
    
    i = 1
    run_up, run_down = True, True
    while run_up or run_down:
        try:
            upper = y[peak_index+i]
            lower = y[peak_index-i]

            if upper <= half_peak and run_up:
                r1 = peak_index + i
                run_up = False
                
            if lower <= half_peak:
                r2 = peak_index - i
                run_down = False

            i+=1

        except IndexError:
            return 25

    FW = (r1-r2)*binsize
    return FW

def gauss_guess(x,y):
    binsize = x[1]-x[0]
    
    peak = np.max(y)
    peak_index = np.where(y == np.max(y))[0][0]
    center = x[peak_index]
    sigma = FWHM(y, peak_index, binsize)/2.355
    
    amp = peak*(sigma*np.sqrt(2*np.pi))

    #print(f'Paramters of gauss_guess \n Center: {center}, height : {peak}, sigma : {sigma} \n')

    d = {'amp': amp, 'center':center, 'sigma' :sigma}
    return d

def gauss(x,y,ref):
    #Fits a Gaussian curve to the data
    supermodel = ConstantModel()+GaussianModel() #Sets the model to fit. The constant model is neded to decrease sensitivity to background noise
    #Guesses for start parameters
    guess = gauss_guess(x,y)

    binsize = x[1]-x[0]
    amp = guess['amp']
    center = guess['center']
    sigma = guess['sigma']

    #print(f'Gauss guess \n Center: {center}, height : {amp}, sigma : {sigma} \n')
    params = supermodel.make_params(amplitude=amp,
                                    center=center,
                                    sigma=sigma,
                                    c=5)
    
    result = supermodel.fit(y, params=params, x=x)
    sigma = result.params['sigma'].value
    center = result.params['center'].value
    height = result.params['height'].value

    intensity = result.params['amplitude']
    return calcDistance(center,ref*binsize), intensity, height

def old_gauss(x,y,ref):
    #Fits a Gaussian curve to the data
    supermodel = ConstantModel()+GaussianModel() #Sets the model to fit. The constant model is neded to decrease sensitivity to background noise
    #Guesses for start parameters
    binsize = x[1]-x[0]
    a_peak = np.max(y)
    t_peak = np.where(y == a_peak)[0][0]*binsize
    avg = np.mean(y)
    params = supermodel.make_params(amplitude=a_peak*(22*np.sqrt(2*np.pi)),
                                    center=t_peak, sigma=22, c=3)
    
    result = supermodel.fit(y, params=params, x=x)
    sigma = result.params['sigma'].value
    center = result.params['center'].value
    height = result.params['amplitude'].value /(sigma*np.sqrt(2*np.pi))
    return calcDistance(center,ref*binsize), height

def skewedgauss(x,y, ref):
    #Fits a SkewedGaussian function to the data
    #Acheives slightly better result on individual pixels but overal performance is worse, not sure why. Probably due to higher sensitivity
    
    supermodel = ConstantModel() + SkewedGaussianModel() #The constant model is neded to decrease sensitivity to background noise
    
    # Start guesses for parameters
    binsize = x[1]-x[0]
    a_peak = np.max(y)
    t_peak = np.where(y == a_peak)[0][0]*binsize
    avg = np.mean(y)
    gamma = -10
    sigma = 200

    params = supermodel.make_params(amplitude = a_peak*sigma*np.sqrt(2*np.pi),
                                    center = t_peak,
                                    sigma = sigma,
                                    gamma = gamma,
                                    c = 3)

    result = supermodel.fit(y, params = params, x = x)
    center = result.params['center'].value

    bestparam = result.params
    X = np.arange(np.min(x),np.max(x), (np.max(x)-np.min(x))/1e6)
    Y = supermodel.eval(params=bestparam, x=X)

    sigma = result.params['sigma'].value
    center = result.params['center'].value
    height = result.params['amplitude'].value / (sigma*np.sqrt(2*np.pi))
    gamma = result.params['gamma'].value

    #print("Skewed Gauss: center, height, sigma, gamma | ", center, height, sigma, gamma)
    
    return calcDistance(center,ref*binsize), height
