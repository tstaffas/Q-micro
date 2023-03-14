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
#import cv2

#Packages used for curve fitting
import lmfit as lm
from lmfit.models import GaussianModel, ConstantModel, SkewedGaussianModel
from lmfit import Parameters

###### Saving data ###########
def create_folder(directory, folder_name):
    """Checks if a folder exists in a directory, otherwise it creates it"""
    
    if not os.path.exists(directory.joinpath(f'{folder_name}')): #If folder does not exist, create it
        os.makedirs(directory.joinpath(f'{folder_name}'))

    return directory.joinpath(f'{folder_name}')

def save_data(resultdict, file_path, save_folder_name = 'analysed data'):
    parent_folder_path = file_path.parent
    save_folder_path = create_folder(parent_folder_path, save_folder_name)
    savename = str(file_path.stem)+'.txt'
    
    x, y, ToF, intensity, height = [],[],[],[],[]
    for p in resultdict:
      
        x.append(p[0])
        y.append(p[1])
        ToF.append(resultdict[p]['ToF'])
        intensity.append(resultdict[p]['intensity'])
        height.append(resultdict[p]['height'])

    savepath = save_folder_path.joinpath(savename)
    np.savetxt(savepath,np.transpose([x,y,ToF, intensity, height]))
  
    
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

###---------- Functions to adjust image for variable swipe-speeds ----------------###

def yVelocityFunc(ampY, yfreq, time): # Returns the velocity-fucntion for the Y function (unit ampere/time) given 
    return ampY * 2 * np.pi * yfreq * np.cos(2 * np.pi * yfreq * time - (np.pi / 2)) 

def yValueFunc(ampY, yfreq, time): # Returns the function for the Y value for the swipe function (unit ampere)
    return ampY * np.sin(2 * np.pi * yfreq * time - (np.pi / 2)) #Measurement should start at peak or valley so it should be phase pi/2 

def xValueFunc(S, time): #assume time start at t=0. # Returns the X value for the swipe function (unit ampere)
    return int(time / S)

def xValueFunc2(ampX, xfreq, time): # Returns the X value for the swipe function (unit ampere)
    return ampX * np.sin(2 * np.pi * xfreq * time) #- (np.pi / 2) #Measurement should start at peak or valley so it should be phase pi/2 

###### Image construction ########


### Method 1: Create a speed adjusted pixel matrix, based on a generalized method for resonant scanning i y-direction and stepwise in x-direction. 
#This method be generalized further independent of scanning patterns in x- and y-direction

def createXYMatrix(dimX, dimY, pixelAY, ampY, xvaluelist, yvaluelist, countrate, time_axis):
    
    imagematrix = [[0]*dimY for i in range(dimX)] # create a 100x100 pixel matrix for the image
    
    yRail = []
    for i in range(dimY): #Create a list with total current over the full intervall (2 * amp) divided into each pixel segment. This will be used to made decision which pixel bin to place the counts
        yRail.append(-ampY + i * pixelAY)

    xRail = []                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
    for i in range(dimX): #Same function as for yrail. This is not used when stepwise but should be modified if we use a resonant function also in the x-direction
        xRail.append(i)

    indexY = 0
    indexX = 0

    for i in range(len(time_axis)): #
        indexX = xvaluelist[i] #Modified xvaluelsit 
        for j in range(1, len(yRail)):
            if yvaluelist[i] >= yRail[j-1] and yvaluelist[i] < yRail[j]:
                indexY = j
        imagematrix[indexX][indexY] += countrate[i]
    return imagematrix                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     


### Method 2: Create a speed adjusted pixel matrix, based on a generalized method for resonant scanning i both x- and y-direction 

def createXYMatrix2(dimX, dimY, pixelAY, pixelAX, ampY, ampX, xvaluelist2, yvaluelist, countrate, time_axis):
    
    imagematrix = [[0]*dimY for i in range(dimX)] # create a 100x100 pixel matrix for the image
    
    yRail = []
    for i in range(dimY): #Create a list with total current over the full intervall (2 * amp) divided into each pixel segment. This will be used to made decision which pixel bin to place the counts
        yRail.append(-ampY + i * pixelAY)

    xRail = []                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
    for i in range(dimX): #Same function as for yrail. This is not used when stepwise but should be modified if we use a resonant function also in the x-direction
        xRail.append(-ampX + i * pixelAX)

    indexY = 0
    indexX = 0

    for i in range(len(time_axis)):
        for j in range(1, len(xRail)):
            if xvaluelist2[i] >= xRail[j-1] and xvaluelist2[i] < xRail[j]:
                indexX = j
        for k in range(1, len(yRail)):
            if yvaluelist[i] >= yRail[k-1] and yvaluelist[i] < yRail[k]:
                indexY = k
        imagematrix[indexX][indexY] += countrate[i]
    return imagematrix  


# Method 3. Create a speed-adjustment pixel matrix, place the right number of bins in each pixel given the swipe speed
def createAdjustedMatrix(dimX, dimY, Sbins, pixelAY, velocitybinlist, countrate):
    pixelpart = [0] * dimY # number of pixels along resonant axis for one swipe up or down (half a period)
    matrix = []
    k = 0
    pixelsum = 0
    ss = 0
    for i in range(dimX): #for each pixel in x-direction
        for j in range(len(pixelpart)): #over each 100 pixels in y-direction (one swipe)
            #print("x-pixel:" + str(i))
            #print("y-pixel:" + str(j))
            while pixelsum < pixelAY and ss < Sbins: # conditions that must be met during each swipe
                pixelsum += abs(velocitybinlist[k]) # as long as the cumulative current contribution is less or equal to pixelA (the constant current per pixel)...
                pixelpart[j] += countrate[k] # ...sum the photon counts to the pixel j
                #print("bin nr: " + str(k))
                #print("swipe bin nr: " + str(ss))
                k +=1
                ss +=1 
            pixelsum = 0 # clear
        ss = 0 # clear
        if (i+1) % 2 != 1:
            pixelpart.reverse() # every even line segment flips
            t = 1
        matrix.append(pixelpart)
        pixelpart = [0] * dimY # clear
    return matrix

# Method 4. Create a non speed adjusted pixel matrix, places an equal amount of bins in each pixel 
def createEqualMatrix(dimX, dimY, Sbins, countrate):
    numbpix = int(Sbins / dimY)
    pixelpart = [0] * dimY
    matrix = []
    k = 0

    for i in range(dimX):
        for j in range(len(pixelpart)):
            for l in range(numbpix):
                pixelpart[j] += countrate[k]
                k +=1
        if (i+1) % 2 != 1:
            pixelpart.reverse()
            t = 1
        matrix.append(pixelpart)
        pixelpart = [0] * dimY
    return matrix

# Method 5. Notice this is the original method that only works for resY = 1e10, where Sbins = dimY = 100. Thus, each bin is a pixel in the y-direction (100 bins = 100 pixels in y-direction)
def createOriginalImage(dimX, dimY, resY, Sbins, countrate): #In this method Sbins = dimY
    r = int(Sbins)
    matrix = []

    for i in range(1, dimX+1):
        part = list(countrate[(i-1)*r:i*r]) #extract a line segment of Sbins = dimY
        if i % 2 != 1:
            part.reverse() # every even line segment flips
            t = 1 # just to have something within the condition if there is no even i
        matrix.append(part)
    return matrix

###--- Set pixel high pass filter ----###
def setHighPassFilter(matrix, threshold, dimX, dimY):
    matrix = np.array(matrix)
    print("Pixels where counts are above the threshold " + str(threshold))
    arglist = np.argwhere(matrix > threshold)
    for i in range(len(arglist)):
        print("position: " + str(arglist[i]) + ", value: " + str(matrix[arglist[i][0], arglist[i][1]]))
    for i in range(dimX):
        for j in range(dimY):
            if matrix[i,j] > threshold:
                matrix[i,j] = threshold
    return matrix

#Dictionary of kernels (filters)

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
            
    xdim = int(np.max(x))+1
    ydim = int(np.max(y))+1
    
    inten = np.array(inten)
    metricmatrix = inten.reshape(xdim,ydim) #Creates a symmetric matrix of the metric data
    norm_metricmatrix=metricmatrix*255/np.max(metricmatrix) #normalize metric values to between pixel values of 0-255
    
    return metricmatrix, norm_metricmatrix, metr

def plot_heatmap(i_matrix, metric, filter, nor, iter, show = False, log = True, file_path = None):
    if log == True:
        norm = LogNorm()
    else:
        norm = None
    plt.figure(num=None, figsize=(10, 8), dpi=150)
    plt.imshow(i_matrix, cmap = cm.brg, norm = norm)
    plt.colorbar()

    if not file_path:
        savepath = metric+"_"+nor+"_"+filter+"_"+"iter_"+str(iter)+".png"

    else:
        folder_name = 'analysed images'
        save_folder_path = create_folder(file_path.parent, folder_name)

        name = str(file_path.name).split('_')[0]
        
        savename = name + metric+"_"+nor+"_"+filter+"_"+"iter_"+str(iter)+".png"
        savepath = save_folder_path.joinpath(savename)
        
        
    plt.savefig(savepath)
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
    #plt.figure(num=None, figsize=(10, 8), dpi=150)
    plt.imshow(image,cmap='gray')
    plt.savefig("grayimage_" + metric + ".png")
    plt.show()
    #plt.close()

    f = np.fft.fft2(image)
    f_s = np.fft.fftshift(f)
    #plt.figure(num=None, figsize=(10, 8), dpi=150) 
    plt.imshow(np.log(abs(f_s)), cmap='gray');
    plt.savefig("fouriertransform_image_" + metric + ".png")
    plt.show()
    #plt.close()

    img_i = np.fft.irfft2(f,image.shape)
    #plt.figure(num=None, figsize=(10, 8), dpi=150)
    plt.imshow(img_i,cmap='gray')
    plt.savefig("inversetransform_image_" + metric + ".png")
    plt.show()
    #plt.close()
