#Packages used for analysis and image construction

from matplotlib import pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import LogNorm
import numpy as np
import numpy.ma as ma

import os
import sys

from skimage.io import imread, imshow
from skimage.color import rgb2yuv, rgb2hsv, rgb2gray, yuv2rgb, hsv2rgb
from skimage.transform import rescale
from scipy.signal import convolve2d

#Another package for image filtering
import cv2

#Packages used for curve fitting
import lmfit as lm
from lmfit.models import GaussianModel, ConstantModel, SkewedGaussianModel
from lmfit import Parameters

###### Image analysis ###########

def calcTof(t_ref,t_signal): #calculates the differnce between times between peak time and reference time in picoseconds
    return t_signal-t_ref

def integral(y, peak_value): #Function to extract intensity, y = histogram
    peak_index = np.where(y == peak_value)[0][0] #Get the index for the max value in the array of count values (in the histogram of 6250 values)
    n = 10 #half interval
    s = 0 #Integral sum
    for j in range(peak_index-n, peak_index+n): #Interval to integrate over
        try:
            s+=y[j] #Summation of the count staples over the interval     
        except IndexError:
            print("Integral failed: Maybe check this out")
            break  
    return s

def peak_metrics(x,y,index_ref): #Function to extract peak, height and intensity from individual histograms for each mirror position
    binsize = x[1]-x[0]  
    height = np.amax(y) #find the peak
    intensity = integral(y, height) #integrate counts over an interval
    tof = calcTof(binsize*index_ref, binsize*np.where(y == height)[0][0]) #time of flight from reference time to where the peak is
    return tof, intensity, height

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
    d = {'amp': amp, 'center': center, 'sigma': sigma}
    return d

def gauss_metrics(x,y,index_ref): #Fits a gaussian curve to the data and then pics out, ToF, Peak, Intensity
    supermodel = ConstantModel() + GaussianModel()
    guess = gauss_guess(x,y)
    binsize = x[1] - x[0]
    amp = guess['amp']
    center = guess['center']
    sigma = guess['sigma']
    params = supermodel.make_params(amplitude = amp, center = center, sigma = sigma, c=5)
    result = supermodel.fit(y, params = params, x = x)
    sigma = result.params['sigma'].value
    height = result.params['height'].value
    intensity = result.params['amplitude'].value

    tof = calcTof(binsize*index_ref, center) #time of flight from reference time to where the peak is
    return tof, intensity, height


###### Image construction ########

#Dictionary of kernels (filters)
# Box Blur
# Gaussian Blur 3x3
# Gaussian Blur 5x5
# Sharpen

KERNELS = {'identity':np.array([[0, 0, 0],
                     [0, 1, 0],
                     [0, 0, 0]]),
           'blur':(1 / 9.0) * np.array([[1, 1, 1],
                                [1, 1, 1],
                                [1, 1, 1]]),
           'gauss33':(1 / 16.0) * np.array([[1, 2, 1],
                                  [2, 4, 2],
                                  [1, 2, 1]]),
           'gauss55':(1 / 256.0) * np.array([[1, 4, 6, 4, 1],
                                   [4, 16, 24, 16, 4],
                                   [6, 24, 36, 24, 6],
                                   [4, 16, 24, 16, 4],
                                   [1, 4, 6, 4, 1]]),
           'sharpen':np.array([[0, -1, 0],
                    [-1, 5, -1],
                    [0, -1, 0]])
    } 


def i_matrix(resultdict, metric): #Creates a matrix with the metric values over the coordinate system
    x = []
    y = []
    inten = []
    #mask = []
    metr = metric #the metric from analysis to make an image of

    for p in resultdict: #MS: walk through dictionary
        x.append(p[0]) #i values
        y.append(p[1]) #j values
        e = resultdict[p][metric]
        inten.append(e)
        
        #Do we need this??
        # if e < max_value and e != 0:
        #     inten.append(e)
        #     mask.append(0) #MS: dont understand
        # else:
        #     inten.append(0) #MS: dont understand
        #     mask.append(1) #MS: dont understand
            
    x = np.array(x)
    y = np.array(y)
    N = int(len(x)**.5)
    
    inten = np.array(inten)
    metricmatrix = inten.reshape(N,N) #Creates a symmetric matrix of the metric data
    norm_metricmatrix=metricmatrix*255/np.max(metricmatrix) #normalize metric values to between pixel values of 0-255
    
    return metricmatrix, norm_metricmatrix, metr

def plot_heatmap(i_matrix, metric, filter, nor, iter, show = False, log = True):
    if log == True:
        norm = LogNorm()
    else:
        norm = None
    plt.figure(num=None, figsize=(10, 8), dpi=150)
    plt.imshow(i_matrix, cmap = cm.brg, norm = norm)
    plt.colorbar()
    plt.savefig(metric+"_"+nor+"_"+filter+"_"+"iter_"+str(iter)+".png")
    if show:
        plt.show()
    plt.close()

def edge_detection(i_matrix):
    up_edge = np.array([[1,2,1],[0,0,0],[-1,-2,-1]])
    down_edge = np.array([[-1,-2,-1],[0,0,0],[1,2,1]])

    right_edge = np.array([[1,0,-1],[2,0,-2],[1,0,-1]])
    left_edge = np.array([[-1,0,1],[-2,0,2],[-1,0,1]])

    edge_1 = convolve2d(i_matrix, up_edge, 'valid')
    edge_2 = convolve2d(i_matrix, down_edge, 'valid')
    edge_3 = convolve2d(i_matrix, left_edge, 'valid')
    edge_4 = convolve2d(i_matrix, right_edge, 'valid')
    
    edge_matrix = np.abs(edge_1)+np.abs(edge_2)+np.abs(edge_3)+np.abs(edge_4)
    return edge_matrix

def convolver(image, kernel, iterations):
    filter = KERNELS[kernel]
    for i in range(iterations):
        image = convolve2d(image, filter, 'same', boundary = 'fill', fillvalue = 0)
    return image

def fouriertransform(image, metric):
    plt.figure(num=None, figsize=(10, 8), dpi=150)
    plt.imshow(image,cmap='gray')
    plt.savefig("grayimage_" + metric + ".png")
    #plt.show()
    plt.close()

    f = np.fft.fft2(image)
    f_s = np.fft.fftshift(f)
    plt.figure(num=None, figsize=(10, 8), dpi=150) 
    plt.imshow(np.log(abs(f_s)), cmap='gray');
    plt.savefig("fouriertransform_image_" + metric + ".png")
    #plt.show()
    plt.close()

    img_i = np.fft.irfft2(f,image.shape)
    plt.figure(num=None, figsize=(10, 8), dpi=150)
    plt.imshow(img_i,cmap='gray')
    plt.savefig("inversetransform_image_" + metric + ".png")
    #plt.show()
    plt.close()
    
