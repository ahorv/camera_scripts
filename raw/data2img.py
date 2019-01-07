#!/usr/bin/env python
from __future__ import division

import matplotlib.pyplot as plt
import numpy as np
np.set_printoptions(threshold=np.nan)
import os
from os import listdir
from os.path import isfile, join
from glob import glob
from numpy.lib.stride_tricks import as_strided
import matplotlib.cm as cm


global images_path
#images_path = r'C:\Hoa_Python_Projects\RemoteDebugEx\hist\input\20171025_140139'  # @home
images_path = r'C:\Users\tahorvat\PycharmProjects\python_scripts\hist\input\20171025_140139'  # @lab

###############################################################
#
# With de-bayering
#
###############################################################

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

def main():
    try:
        global images_path

        images_path = images_path + '/data5_.data'
        data = np.fromfile(images_path, dtype='uint16')
        data = data.reshape([2464, 3296])

        # IMX219 sensors Bayer pattern : BGGR -> https://ch.mathworks.com/help/images/ref/demosaic.html
        # BGBGBGBGBGBGBG
        # GRGRGRGRGRGRGR
        # BGBGBGBGBGBGBG
        # GRGRGRGRGRGRGR

        # De-Bayering
        rgb = np.zeros(data.shape + (3,), dtype=data.dtype)
        rgb[1::2, 0::2, 0] = data[1::2, 0::2]  # Red
        rgb[0::2, 0::2, 1] = data[0::2, 0::2]  # Green
        rgb[1::2, 1::2, 1] = data[1::2, 1::2]  # Green
        rgb[0::2, 1::2, 2] = data[0::2, 1::2]  # Blue

        output = demosaic(rgb)

        rgb_img = (output >> 2).astype(np.uint8)

        plt.imshow(rgb_img,interpolation='nearest', cmap=cm.binary)
        plt.show()

        # plt.imshow(rgb_img)
        # plt.show()

    except Exception as e:
        print('Error in Main: ' + str(e))


if __name__ == '__main__':
    main()
