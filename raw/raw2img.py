#!/usr/bin/env python
from __future__ import division

import numpy as np
import matplotlib.pyplot as plt
import cv2
import exifread
from fractions import Fraction
import shutil
import numpy as np
np.set_printoptions(threshold=np.nan)
from glob import glob
from numpy.lib.stride_tricks import as_strided
import matplotlib.cm as cm
import scipy
from scipy import ndimage
import imageio


global images_path
global output_path
#images_path = r'C:\Hoa_Python_Projects\RemoteDebugEx\hist\input\20171025_140139'  # @home
#images_path = r'C:\Users\tahorvat\PycharmProjects\python_scripts\hist\input\20171025_140139'  # @lab
#output_path = r'C:\Users\tahorvat\PycharmProjects\python_scripts\hist\output'

images_path = r'C:\Users\tahorvat\Desktop\20180409_090414'
output_path = r'C:\Users\tahorvat\Desktop\20180409_090414'


def load_data_as_img():
    try:
        print("imagehelpers loaded!")
        data_arrays = []
        for data in sorted(glob(images_path + '/*.data')):
            #load binary file to array
            np_arr = np.fromfile(data,dtype=np.uint16)
            np_arr.reshape(3296,2464)
            data_arrays.append(np_arr)
        return data_arrays

    except Exception as e:
        print('Could not load image: ' + str(e))

def demosaic(rgb):
    # construct bayer-filter for de-mosaicing
    bayer = np.zeros(rgb.shape, dtype=np.uint8)
    bayer[1::2, 0::2, 0] = 1  # Red
    bayer[0::2, 0::2, 1] = 1  # Green
    bayer[1::2, 1::2, 1] = 1  # Green
    bayer[0::2, 1::2, 2] = 1  # Blue

    # Allocate an array to hold output
    output = np.empty(rgb.shape, dtype=rgb.dtype)
    window = (3, 3)
    borders = (window[0] - 1, window[1] - 1)
    border = (borders[0] // 2, borders[1] // 2)

    # pad rgb and bayer arrays
    rgb = np.pad(rgb, [
        (border[0], border[0]),
        (border[1], border[1]),
        (0, 0),
    ], 'constant')
    bayer = np.pad(bayer, [
        (border[0], border[0]),
        (border[1], border[1]),
        (0, 0),
    ], 'constant')
    # finally de-mosaic by weighted average:
    for plane in range(3):
        p = rgb[..., plane]
        b = bayer[..., plane]
        pview = as_strided(p, shape=(
            p.shape[0] - borders[0],
            p.shape[1] - borders[1]) + window, strides=p.strides * 2)
        bview = as_strided(b, shape=(
            b.shape[0] - borders[0],
            b.shape[1] - borders[1]) + window, strides=b.strides * 2)
        psum = np.einsum('ijkl->ij', pview)
        bsum = np.einsum('ijkl->ij', bview)
        output[..., plane] = psum // bsum

        # output contains the de-mosaciced image but to view it, it must be
        # convert to 8-bit RGB data:

    return output

###############################################################
#
# Nach Matlabscript
#
###############################################################


def main():
    try:
        global images_path
        #data_stack = []
        #data_stack = load_data_as_img()
        #raw = data_stack[0]

        images_path = images_path + '/data5_.data'
        data = np.fromfile(images_path, dtype='uint16') #  np.uint8
        data = data.reshape([2464, 3296])

        # IMX219 sensors Bayer pattern : BGGR -> https://ch.mathworks.com/help/images/ref/demosaic.html
        # BGBGBGBGBGBGBG
        # GRGRGRGRGRGRGR
        # BGBGBGBGBGBGBG
        # GRGRGRGRGRGRGR

        # Sort to pages p1 to p3 (Green = 1/2(p2+p3) )
        p1 = data[0::2, 1::2]  # Blue
        p2 = data[0::2, 0::2]  # Green
        p3 = data[1::2, 1::2]  # Green
        p4 = data[1::2, 0::2]  # Red

        blue = p1
        green = ((p2+p3))/2
        red = p4

        gamma = 1.0         # gamma correction
        # b, g and r gain;  wurden rausgelesen aus den picam Aufnahmedaten
        vb = 1.0       # 87 / 64.  = 1.359375
        vg = 1.0           # 1.
        vr = 1.0     # 235 / 128.  = 1.8359375

        # color conversion matrix (from raspi_dng/dcraw)
        # R        g        b
        cvm = np.array(
            [[1.20, -0.30, 0.00],
             [-0.05, 0.80, 0.14],
             [0.20, 0.20, 0.7]])

        s = (1232, 1648, 3)
        rgb = np.zeros(s)
        rgb[:, :, 0] = vr * 1023 * (red / 1023.) ** gamma
        rgb[:, :, 1] = vg * 1023 * (green / 1023.) ** gamma
        rgb[:, :, 2] = vb * 1023 * (blue / 1023.) ** gamma

        #db_rgb = rgb.dot(cvm)

        rgb = (rgb - np.min(rgb)) / (np.max(rgb) - np.min(rgb))    # normalize image

        plt.imshow(rgb,interpolation='nearest', cmap=cm.binary)
        #plt.title('raw2img.py  RGB')
        plt.show()

        output = (rgb/256).astype('uint8')
        with open(output_path + '/raw2img.jpeg', 'wb') as f:
            output.tofile(f)

    except Exception as e:
        print('Error in Main: ' + str(e))


if __name__ == '__main__':
    main()
