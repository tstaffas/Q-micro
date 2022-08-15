from matplotlib import pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import LogNorm
import numpy as np
import numpy.ma as ma

import os
from skimage.io import imread, imshow
from skimage.color import rgb2gray
from skimage.transform import rescale
from scipy.signal import convolve2d

#KERNELS
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

# Box Blur
# Gaussian Blur 3x3
# Gaussian Blur 5x5
# Sharpen

def intensity_matrix(i_data, max_value, min_value = 10, kernel = KERNELS['identity'], tol = 1):
    x,y,i, mask = [], [], [], []
    for p in i_data:
        e = i_data[p]
        x.append(p[0])
        y.append(p[1])

        
        if e < max_value and e != 0:
            i.append(e)
            mask.append(0)
        else:
            i.append(0)
            mask.append(1)
            
    x = np.array(x)
    y = np.array(y)
    i = ma.array(i, mask = mask)
    N = int(len(x)**.5)
    
    i = np.array(i)
    i = i.reshape(N,N)
    i = np.rot90(i, k=-1)

    mx = ma.masked_values(i, 0, atol = tol)
    mx = convolve2d(mx, kernel, 'valid')
    mx = ma.masked_values(mx, 0, atol = tol)
        
    return mx

def plot_heatmap(i_matrix, file = None, save = False, folder_name = 'heatmaps', name = 'heatmap', show = True, log = True):
    if log == True:
        norm = LogNorm()
    else:
        norm = None
    plt.imshow(i_matrix, cmap = cm.brg, norm = norm)
    #plt.imshow(i, extent = (np.min(y), np.max(y), np.min(x), np.max(x)), interpolation = 'nearest', cmap = cm.brg)#, norm = LogNorm())

    plt.colorbar()
    

    #save figure
    if save:
        if not os.path.exists(file.parent.joinpath(folder_name)): #If folder does not exist, create it
            os.makedirs(file.parent.joinpath(folder_name))

        filename = name+file.stem+'_heatmap.png'
        savepath = file.parent.joinpath(folder_name, filename)
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

    plot_heatmap(edge_matrix)
    return edge_matrix

    
    
