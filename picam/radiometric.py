#!/usr/bin/env python

import cv2
import io
import os
import time
import sys
from glob import glob
from os.path import join
import logging
import logging.handlers
from matplotlib import pyplot as plt
import numpy as np
import math

if sys.platform == "linux":
    import picamera
    import pwd
    import grp
    import stat


print('Version opencv: ' + cv2.__version__)

######################################################################
## Hoa: 15.10.2018 Version 2 : radiometric.py
######################################################################
# According to 'Laying foundation to use Raspberry Pi 3 V2 camera'.
# Purpos: Absolute Radiometric Calibration of Raspberry pi 3 V2 camera
# Comprises:
# - Darkframe substraction
# - Flat fielding
# - Radiometric correction
#
# New /Changes:
# ----------------------------------------------------------------------
#
# 11.10.2018 : First implementation
#
#
######################################################################

global SCRIPTPATH
global RADIOMETRICALIB
global DARKFRAMES_5MS
global DARKFRAMES_50MS
global DF_AVG5MS
global DF_AVG50MS
global WHITEFRAMES_5MS
global WHITEFRAMES_50MS
global WF_AVG5MS
global WF_AVG50MS

SCRIPTPATH = join('/home', 'pi', 'python_scripts', 'picam')
#SCRIPTPATH = r'C:\Users\tahorvat\Desktop'

RADIOMETRICALIB = join(SCRIPTPATH, 'radiometric')
#RADIOMETRICALIB = join(SCRIPTPATH, 'test')
DARKFRAMES_5MS = join(RADIOMETRICALIB, 'df5')
DARKFRAMES_50MS = join(RADIOMETRICALIB, 'df50')
DF_AVG5MS  = join(RADIOMETRICALIB, 'df_avg5ms.data')
DF_AVG50MS = join(RADIOMETRICALIB, 'df_avg50ms.data')
WHITEFRAMES_5MS = join(RADIOMETRICALIB, 'wf5')
WHITEFRAMES_50MS = join(RADIOMETRICALIB, 'wf50')
WF_AVG5MS  = join(RADIOMETRICALIB, 'wf_avg5ms.data')
WF_AVG50MS = join(RADIOMETRICALIB, 'wf_avg50ms.data')
DATAPATH = join(RADIOMETRICALIB, 'wf5','1_wf.data')
print(DATAPATH)


class Logger:
    def __init__(self):
        self.logger = None

    def getLogger(self, newLogPath=None):

        try:
            global SCRIPTPATH

            if newLogPath is None:
                LOGFILEPATH = os.path.join(SCRIPTPATH, 'radiometric.log')
                logFormatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
                fileHandler = logging.FileHandler(LOGFILEPATH)
                name = 'rootlogger'
            else:
                LOGFILEPATH = newLogPath
                logFormatter = logging.Formatter('%(message)s')
                fileHandler = logging.FileHandler(LOGFILEPATH)
                name = 'radiometricLogger'

            # configure file handler
            fileHandler.setFormatter(logFormatter)

            # configure stream handler
            consoleHandler = logging.StreamHandler()
            consoleHandler.setFormatter(logFormatter)

            # get the logger instance
            self.logger = logging.getLogger(name)

            # set the logging level
            self.logger.setLevel(logging.INFO)

            if not len(self.logger.handlers):
                self.logger.addHandler(fileHandler)
                self.logger.addHandler(consoleHandler)

            helper = Helpers()
            if sys.platform == "linux":
                helper.setOwnerAndPermission(LOGFILEPATH)
            return self.logger

        except IOError as e:
            print('Error logger:' + str(e))

    def closeLogHandler(self):
        try:
            handlers = self.logger.handlers[:]
            for handler in handlers:
                handler.close()
                self.logger.removeHandler(handler)

        except IOError as e:
            print('Error logger:' + str(e))

class Helpers:

    def createNewFolder(self, thispath):
        try:
            if not os.path.exists(thispath):
                os.makedirs(thispath)
                self.setOwnerAndPermission(thispath)

        except IOError as e:
            print('DIR : Could not create new folder: ' + str(e))

    def setOwnerAndPermission(self, pathToFile):
        try:
            uid = pwd.getpwnam('pi').pw_uid
            gid = grp.getgrnam('pi').gr_gid
            os.chown(pathToFile, uid, gid)
            os.chmod(pathToFile, 0o777)
        except IOError as e:
            print('PERM : Could not set permissions for file: ' + str(e))

class Color_Balance:

    def apply_mask(self, matrix, mask, fill_value):
        masked = np.ma.array(matrix, mask=mask, fill_value=fill_value)
        return masked.filled()

    def apply_threshold(self, matrix, low_value, high_value):
        low_mask = matrix < low_value
        matrix = self.apply_mask(matrix, low_mask, low_value)

        high_mask = matrix > high_value
        matrix = self.apply_mask(matrix, high_mask, high_value)

        return matrix

    def simplest_cb(self, path_to_image, percent):

        imprc = Imgproc()
        data = np.fromfile(path_to_image, dtype='uint16')
        data = data.reshape([2464, 3296])
        img = imprc.demosaic1(data)

        assert img.shape[2] == 3
        assert percent > 0 and percent < 100

        half_percent = percent / 200.0

        channels = cv2.split(img)

        out_channels = []
        for channel in channels:
            assert len(channel.shape) == 2
            # find the low and high precentile values (based on the input percentile)
            height, width = channel.shape
            vec_size = width * height
            flat = channel.reshape(vec_size)

            assert len(flat.shape) == 1

            flat = np.sort(flat)

            n_cols = flat.shape[0]

            low_val = flat[math.floor(n_cols * half_percent)]
            high_val = flat[math.ceil(n_cols * (1.0 - half_percent))]

            print("Lowval: ", low_val)
            print("Highval: ", high_val)

            # saturate below the low percentile and above the high percentile
            thresholded = self.apply_threshold(channel, low_val, high_val)
            # scale the channel
            img_16bit = (2**16) -1
            img_8bit = 255
            normalized = cv2.normalize(thresholded, thresholded.copy(), 0, img_16bit, cv2.NORM_MINMAX)
            out_channels.append(normalized)
            img = cv2.merge(out_channels)
            img = imprc.toRGB_1(img)
        return img

class Imgproc:

    def demosaic1(self, mosaic, awb_gains = None):
        try:
            black = mosaic.min()
            saturation = mosaic.max()

            uint14_max = 2 ** 14 - 1
            mosaic -= black  # black subtraction
            mosaic *= int(uint14_max / (saturation - black))
            mosaic = np.clip(mosaic, 0, uint14_max)  # clip to range


            if awb_gains is None:
                vb_gain = 1.0
                vg_gain = 1.0  # raspi raw has already gain = 1 of green channel
                vr_gain = 1.0
            else:
                vb_gain = awb_gains[1]
                vg_gain = 1.0  # raspi raw has already gain = 1 of green channel
                vr_gain = awb_gains[0]

            mosaic = mosaic.reshape([2464, 3296])
            mosaic = mosaic.astype('float')
            mosaic[0::2, 1::2] *= vb_gain  # Blue
            mosaic[1::2, 0::2] *= vr_gain  # Red
            mosaic = np.clip(mosaic, 0, uint14_max)  # clip to range
            mosaic *= 2 ** 2

            # demosaic
            p1 = mosaic[0::2, 1::2]  # Blue
            p2 = mosaic[0::2, 0::2]  # Green
            p3 = mosaic[1::2, 1::2]  # Green
            p4 = mosaic[1::2, 0::2]  # Red

            blue = p1
            green = np.clip((p2 // 2 + p3 // 2), 0, 2 ** 16 - 1)
            red = p4

            image = np.dstack([red, green, blue])  # 16 - bit 'image'

            # down sample to RGB 8 bit image use: self.deraw2rgb1(image)

            return image

        except Exception as e:
            print('Error in demosaic1: {}'.format(e))

    def demosiac2(self, data, awb_gains = None):
        try:
            p1 = data[0::2, 1::2]  # Blue
            p2 = data[0::2, 0::2]  # Green
            p3 = data[1::2, 1::2]  # Green
            p4 = data[1::2, 0::2]  # Red

            blue = p1
            green = ((p2 + p3)) / 2
            red = p4

            if awb_gains is None:
                vb_gain = 1.3
                vr_gain = 1.8
            else:
                vb_gain = awb_gains[1]
                vr_gain = awb_gains[0]

            gamma = 1  # gamma correction
            vb = vb_gain
            vg = 1
            vr = vr_gain

            # color conversion matrix (from raspi_dng/dcraw)
            # R        g        b
            cvm = np.array(
                [[1.20, -0.30, 0.00],
                 [-0.05, 0.80, 0.14],
                 [0.20, 0.20, 0.7]])

            s = (1232, 1648, 3)
            rgb = np.zeros(s)

            rgb[:, :, 0] = vr * 1023 * (red / 1023.)   ** gamma
            rgb[:, :, 1] = vg * 1023 * (green / 1023.) ** gamma
            rgb[:, :, 2] = vb * 1023 * (blue / 1023.)  ** gamma

            # rgb = rgb.dot(cvm)

            rgb = (rgb - np.min(rgb)) / (np.max(rgb) - np.min(rgb))

            height, width = rgb.shape[:2]

            img = cv2.resize(rgb, (width, height), interpolation=cv2.INTER_CUBIC) # 16 - bit 'image'

            # down sample to RGB 8 bit image, use: self.deraw2rgb2(data)

            return img

        except Exception as e:
            print('data2rgb: Could not convert data to rgb: ' + str(e))

    def toRGB_1(self, data):
        '''
        Belongs to deraw1
        :param data:
        :return:
        '''
        image = data // 256  # reduce dynamic range to 8 bpp
        image = np.clip(image, 0, 255).astype(np.uint8)

        return image

    def toRGB_2(self, data):
        '''
        Belongs to deraw2
        :param data:
        :return:
        '''
        image = np.zeros(data.shape, dtype=np.float)
        min = data.min()
        image = data - min

        # get the max from out after normalizing to 0
        max = image.max()
        image *= (255 / max)
        image = np.uint8(image)

        return image

    def average_darkframes(self):
        print('Running df averaging.')
        helper = Helpers()
        s = Logger()
        logger = s.getLogger()
        imprc = Imgproc()

        files_5ms = []
        files_50ms = []

        for file in sorted(glob(os.path.join(DARKFRAMES_5MS, "*.data"))):
            if os.path.isfile(file):
                files_5ms.append(file)

        for file in sorted(glob(os.path.join(DARKFRAMES_50MS, "*.data"))):
            if os.path.isfile(file):
                files_50ms.append(file)

        average_5ms = np.fromfile(files_5ms[0], dtype='uint16') # load first image
        average_5ms = average_5ms.reshape([2464, 3296])
        average_5ms = average_5ms.astype('float')
        legend = 'DF 5ms: {df_name}: mean: {df_mean}, median: {df_medi}, std: {df_stdv}, var: {df_var}'

        for file in files_5ms[1:]:
            data = np.fromfile(file, dtype='uint16')
            df = data.reshape([2464, 3296])
            df = df.astype('float')                     # sonst Überlauf
            average_5ms += df

            stats = dict(
                df_name = '{}'.format(file.strip('.data').split('/')[-1]),
                df_mean = '{0:.2f}'.format(np.mean(df)),
                df_medi = '{0:.2f}'.format(np.median(df)),
                df_stdv = '{0:.2f}'.format(np.std(df)),
                df_var  = '{0:.2f}'.format(np.var(df)),
            )
            print(legend.format(**stats))
            logger.info(legend.format(**stats))

        average_5ms /=len(files_5ms)

        img = imprc.demosaic1(average_5ms.astype('uint16'))
        avrg_5ms = imprc.toRGB_1(img)
        cv2.imwrite(join(RADIOMETRICALIB ,"df_avg5ms.jpg"),avrg_5ms)

        with open(RADIOMETRICALIB + "/" + 'df_avg5ms.data', 'wb') as g:
            data = average_5ms.astype('uint16')
            data.tofile(g)
        #-------------------------------------------
        # do the same with 50ms exposure dark frames
        average_50ms = np.fromfile(files_50ms[0], dtype='uint16') # load first image
        average_50ms = average_50ms.reshape([2464, 3296])
        average_50ms = average_50ms.astype('float')
        legend = 'DF 50ms: {df_name}: mean: {df_mean}, median: {df_medi}, std: {df_stdv}, var: {df_var}'

        for file in files_50ms[1:]:
            data = np.fromfile(file, dtype='uint16')
            df = data.reshape([2464, 3296])
            df = df.astype('float')                     # sonst Überlauf
            average_50ms += df

            stats = dict(
                df_name = '{}'.format(file.strip('.data').split('/')[-1]),
                df_mean = '{0:.2f}'.format(np.mean(df)),
                df_medi = '{0:.2f}'.format(np.median(df)),
                df_stdv = '{0:.2f}'.format(np.std(df)),
                df_var  = '{0:.2f}'.format(np.var(df)),
            )
            print(legend.format(**stats))

        average_50ms /= len(files_5ms)

        img = imprc.demosaic1(average_50ms.astype('uint16'))
        avrg_50ms = imprc.toRGB_1(img)
        cv2.imwrite(join(RADIOMETRICALIB,"df_avg50ms.jpg"),avrg_50ms)

        with open(RADIOMETRICALIB + "/" + 'df_avg50ms.data', 'wb') as g:
            data = average_50ms.astype('uint16')
            data.tofile(g)

        logger.info('Created avreged darkframes for 5ms and 50 ms exposure.')
        print('Done avreaging darkframes.')

    def average_whiteframes(self):
        print('Running wf averaging.')
        helper = Helpers()
        s = Logger()
        logger = s.getLogger()
        imprc = Imgproc()

        files_5ms = []
        files_50ms = []

        for file in sorted(glob(os.path.join(WHITEFRAMES_5MS, "*.data"))):
            if os.path.isfile(file):
                files_5ms.append(file)

        for file in sorted(glob(os.path.join(WHITEFRAMES_50MS, "*.data"))):
            if os.path.isfile(file):
                files_50ms.append(file)

        average_5ms = np.fromfile(files_5ms[0], dtype='uint16') # load first image
        average_5ms = average_5ms.reshape([2464, 3296])
        average_5ms = average_5ms.astype('float')
        legend = 'DF 5ms: {wf_name}: mean: {wf_mean}, median: {wf_medi}, std: {wf_stdv}, var: {wf_var}'

        for file in files_5ms[1:]:
            data = np.fromfile(file, dtype='uint16')
            wf = data.reshape([2464, 3296])
            ff = wf.astype('float')                     # sonst Überlauf
            average_5ms += wf

            stats = dict(
                wf_name = '{}'.format(file.strip('.data').split('/')[-1]),
                wf_mean = '{0:.2f}'.format(np.mean(wf)),
                wf_medi = '{0:.2f}'.format(np.median(wf)),
                wf_stdv = '{0:.2f}'.format(np.std(wf)),
                wf_var  = '{0:.2f}'.format(np.var(wf)),
            )
            print(legend.format(**stats))
            logger.info(legend.format(**stats))

        average_5ms /=len(files_5ms)

        img = imprc.demosaic1(average_5ms.astype('uint16'))
        avrg_5ms = imprc.toRGB_1(img)
        cv2.imwrite(join(RADIOMETRICALIB ,"wf_avg5ms.jpg"),avrg_5ms)

        with open(RADIOMETRICALIB + "/" + 'wf_avg5ms.data', 'wb') as g:
            data = average_5ms.astype('uint16')
            data.tofile(g)
        #-------------------------------------------
        # do the same with 50ms exposure dark frames
        average_50ms = np.fromfile(files_50ms[0], dtype='uint16') # load first image
        average_50ms = average_50ms.reshape([2464, 3296])
        average_50ms = average_50ms.astype('float')
        legend = 'WF 50ms: {wf_name}: mean: {wf_mean}, median: {wf_medi}, std: {wf_stdv}, var: {wf_var}'

        for file in files_50ms[1:]:
            data = np.fromfile(file, dtype='uint16')
            wf = data.reshape([2464, 3296])
            wf = wf.astype('float')                     # sonst Überlauf
            average_50ms += wf

            stats = dict(
                wf_name = '{}'.format(file.strip('.data').split('/')[-1]),
                wf_mean = '{0:.2f}'.format(np.mean(wf)),
                wf_medi = '{0:.2f}'.format(np.median(wf)),
                wf_stdv = '{0:.2f}'.format(np.std(wf)),
                wf_var  = '{0:.2f}'.format(np.var(wf)),
            )
            print(legend.format(**stats))

        average_50ms /= len(files_5ms)

        img = imprc.demosaic1(average_50ms.astype('uint16'))
        avrg_50ms = imprc.toRGB_1(img)
        cv2.imwrite(join(RADIOMETRICALIB,"wf_avg50ms.jpg"),avrg_50ms)

        with open(RADIOMETRICALIB + "/" + 'wf_avg50ms.data', 'wb') as g:
            data = average_50ms.astype('uint16')
            data.tofile(g)

        logger.info('Created avreged whiteframes for 5ms and 50 ms exposure.')
        print('Done avreaging white frames.')

    def substract_darkframes(self, data):
        df_avg5ms  = np.fromfile(join(RADIOMETRICALIB,'df_avg5ms.data'),  dtype='uint16')
        df_avg50ms = np.fromfile(join(RADIOMETRICALIB,'df_avg50ms.data'), dtype='uint16')
        df_avg = (np.array(df_avg5ms) + np.array(df_avg50ms)) / 2
        df_substracted = data - df_avg
        return df_substracted.clip(0)

    def create_flatfield(self):
        # Normalize prob:
        # https://stackoverflow.com/questions/40645985/opencv-python-normalize-image

        s = (1232, 1648, 3)
        # white_frame =  np.zeros(s,np.float)  # empty (white) frame
        white_frame = np.ones(s, np.float)
        # coefs for the red channel:
        a0_r = -1.234; a1_r = 1.962;  b1_r = -1.751; a2_r = 0.2604;  b2_r = 0.07941;  w_r = -0.0007905
        # coefs for the green channel:
        a0_g = 0.4900; a1_g = 0.4123; b1_g = 0.1851; a2_g = 0.09083; b2_g = -0.05701; w_g = 0.001312
        # coefs for the green channel:
        a0_b = 0.4935; a1_b = 0.4216; b1_b = 0.1736; a2_b = 0.08101; b2_b = -0.06155; w_b = 0.001284

        #f_r = lambda x: a0_r + a1_r*np.cos(w_r*x) + b1_r*np.sin(w_r*x) + a2_r*np.cos(2*w_r*x) + b2_r*np.sin(2*w_r*x)
        #f_g = lambda x: a0_g + a1_g*np.cos(w_g*x) + b1_g*np.sin(w_g*x) + a2_g*np.cos(2*w_g*x) + b2_g*np.sin(2*w_g*x)
        #f_b = lambda x: a0_b + a1_b*np.cos(w_b*x) + b1_b*np.sin(w_b*x) + a2_b*np.cos(2*w_b*x) + b2_b*np.sin(2*w_b*x)

        red   = white_frame[:, :, 0]
        green = white_frame[:, :, 1]
        blue  = white_frame[:, :, 2]

        # normalize pixel values to [0,1]
        #norm_red   = cv2.normalize(red,   None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        #norm_green = cv2.normalize(green, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        #norm_blue  = cv2.normalize(blue,  None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)

        #r_f = f_r(red)
        #g_f = f_g(green)
        #b_f = f_b(blue)

        f_r = a0_r + a1_r*np.cos(w_r*red)   + b1_r*np.sin(w_r*red)  + a2_r*np.cos(2*w_r*red)  + b2_r*np.sin(2*w_r*red)
        f_g = a0_g + a1_g*np.cos(w_g*green) + b1_g*np.sin(w_g*green)+ a2_g*np.cos(2*w_g*green)+ b2_g*np.sin(2*w_g*green)
        f_b = a0_b + a1_b*np.cos(w_b*blue)  + b1_b*np.sin(w_b*blue) + a2_b*np.cos(2*w_b*blue) + b2_b*np.sin(2*w_b*blue)

        print('min: {} | max: {} | max-min={}'.format(f_r.min(), f_r.max(),f_r.max()-f_r.min()))
        print('min: {} | max: {} | max-min={}'.format(f_g.min(), f_g.max(),f_g.max()-f_g.min()))
        print('min: {} | max: {} | max-min={}'.format(f_b.min(), f_b.max(),f_b.max()-f_b.min()))

        print('f_r test: {}'.format(f_r.dtype))
        np.set_printoptions(formatter={'float': '{: 0.10f}'.format})
        print(f_r)

        # remap to (2^16) - 1 pixel values
        upper_limit = (2**16) - 1        # 16 bit
        red   = cv2.normalize(f_r, f_r, alpha=0, beta=65535, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        green = cv2.normalize(f_g, f_g, alpha=0, beta=65535, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        blue  = cv2.normalize(f_b, f_b, alpha=0, beta=65535, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)

        #a = numpy.array([1.0, 2.0, 3.0], dtype=numpy.float32)


        test = np.array([0.81638017, 0.81638017,0.81638017, 0.81638017, 0.81638017, 0.81638017])
        print('Type test: {}'.format(test.dtype))
        norm_image = cv2.normalize(test, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)

        image = np.dstack([red, green, blue])

        return image          # 16 bit image

    def flatfielding(self, data):
        #Flat fielding for each demosaiced rgb channel

        #data = data.astype('float')
        # numpy functions on arrays:
        # https://jakevdp.github.io/PythonDataScienceHandbook/02.03-computation-on-arrays-ufuncs.html
        # https://stackoverflow.com/questions/24580993/calling-functions-with-parameters-using-a-dictionary-in-python

        # coefs for the red channel:
        a0_r = -1.234; a1_r = 1.962;  b1_r = -1.751; a2_r = 0.2604;  b2_r = 0.07941; w_r = -0.0007905
        # coefs for the green channel:
        a0_g = 0.4900; a1_g = 0.4123; b1_g = 0.1851; a2_g = 0.09083; b2_g = -0.05701; w_g = 0.001312
        # coefs for the green channel:
        a0_b = 0.4935; a1_b = 0.4216; b1_b = 0.1736; a2_b = 0.08101; b2_b = -0.06155; w_b = 0.001284

        f_r = lambda x: a0_r + a1_r*np.cos(w_r*x) + b1_r*np.sin(w_r*x) + a2_r*np.cos(2*w_r*x) + b2_r*np.sin(2*w_r*x)
        f_g = lambda x: a0_g + a1_g*np.cos(w_g*x) + b1_g*np.sin(w_g*x) + a2_g*np.cos(2*w_g*x) + b2_g*np.sin(2*w_g*x)
        f_b = lambda x: a0_b + a1_b*np.cos(w_b*x) + b1_b*np.sin(w_b*x) + a2_b*np.cos(2*w_b*x) + b2_b*np.sin(2*w_b*x)

        red   = data[:, :, 0]
        green = data[:, :, 1]
        blue  = data[:, :, 2]

        # normalize pixel values to [0,1]
        norm_red   = cv2.normalize(red,   None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        norm_green = cv2.normalize(green, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        norm_blue  = cv2.normalize(blue,  None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)

        r_f = f_r(norm_red)
        r_g = f_g(norm_green)
        r_b = f_b(norm_blue)

        # remap to (2^16) - 1 pixel values
        upper_limit = (2**16) - 1        # 16 bit
        red   = cv2.normalize(red,   None, alpha=0, beta=upper_limit, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_16U)
        green = cv2.normalize(green, None, alpha=0, beta=upper_limit, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_16U)
        blue  = cv2.normalize(blue,  None, alpha=0, beta=upper_limit, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_16U)

        image = np.dstack([red, green, blue])

        return image          # 16 bit image

    def plot_data_histogram(self,path_to_image):

        '''
        Plots histogram of one *.data 'image'.

        :param path_to_image: the path to a single *.data image.
        :return: nil
        '''

        print('Plotting data histogram, may take a while !')
        if path_to_image:
            data = np.fromfile(path_to_image, dtype='uint16')
            plt.hist(data, bins= (65536 - 1)) # 65536 -1
            plt.xlim([0, 100])
            plt.title('Histogram for data')
            plt.show()


class Camera_config(object):

  def __init__(self, config_map={}):
      self.camera_ID = config_map.get('camera_ID', 0)
      self.w = config_map.get('w', 2592)
      self.h = config_map.get('h', 1944)
      self.iso = config_map.get('iso', 100)
      self.framerate_max = config_map.get('framrate_max',15)
      self.framerate_min = config_map.get('framrate_min', 1)

  def to_dict(self):
    return {
      'camera_ID': self.camera_ID,
      'w': self.w,
      'h': self.h,
      'iso': self.iso,
      'framerate_max': self.framerate_max,
      'framerate_min': self.framerate_min,
    }


class Camera:

    def __init__(self, picam_instance, config=None):
        if config == None:
            config = Camera_config({})
        self.config = config
        self.camera = picam_instance
        self.camera.resolution = (config.w, config.h)
        self.camera.iso = config.iso

        print('Initializing camera...')
        time.sleep(2)

        self.camera.framerate = config.framerate_min
        self.camera.shutter_speed = self.camera.exposure_speed
        self.camera.exposure_mode = 'off'

        awb_gains = self.camera.awb_gains
        self.camera.awb_mode = 'off'

        print("Set up picam with: ")
        print("\tAWB gains:\t", awb_gains)
        print("\tPicture size   :\t", config.w, 'x', config.h)

    def single_shoot_data(self, iso = None, shutter_speed=None):
        '''
        Takes a single image in raw and returns it as numpy array.
        :param resize_width:  new image width
        :param resize_hight:  new image heigth
        :param shutter_speed: overwrite shuter speed in config file
        :param config: current camera settings
        :param state:  current state
        :return: image as numpy array
        '''
        s = Logger()
        logger = s.getLogger()
        config = self.config

        # update camera parameters
        self.camera.ISO = iso
        self.camera.resolution = (config.w, config.h)
        self.camera.shutter_speed = shutter_speed

        stream = io.BytesIO()
        self.camera.capture(stream, format='jpeg',bayer=True)

        data = stream.getvalue()[-10270208:]
        data = data[32768:4128 * 2480 + 32768]
        data = np.fromstring(data, dtype=np.uint8)
        data = data.reshape((2480, 4128))[:2464, :4120]
        data = data.astype(np.uint16) << 2
        for byte in range(4):
            data[:, byte::5] |= ((data[:, 4::5] >> ((4 - byte) * 2)) & 0b11)

        data = np.delete(data, np.s_[4::5], 1)

        cam_stats = dict(
            ss = self.camera.shutter_speed,
            iso= self.camera.iso,
            exp= self.camera.exposure_speed,
            ag = self.camera.analog_gain,
            dg = self.camera.digital_gain,
            awb= self.camera.awb_gains,
            br = self.camera.brightness,
            ct = self.camera.contrast,
        )
        logdata = '[ss:{ss}, iso:{iso} exp:{exp}, ag:{ag}, dg:{dg}, awb:[{awb}], br:{br}, ct:{ct}]'.format(**cam_stats)
        logger.info(logdata)

        return data

    def warm_up(self):
        s = Logger()
        logger = s.getLogger()

        iso = 100
        ss = 5000

        print('Warm up will take some time!')

        for i in range(2):
            self.single_shoot_data(iso,ss)
            print('{} left'.format(25-i))

        print('Warm up done!')
        logger.info('Warm up done.')

    def take_darkframe_pictures(self):
        helper = Helpers()
        s = Logger()
        logger = s.getLogger()

        five_ms =  5 * 1000  # shutterspeed is in units of microseconds
        fity_ms = 50 * 1000
        iso = 100

        helper.createNewFolder(DARKFRAMES_5MS)
        helper.createNewFolder(DARKFRAMES_50MS)

        for i0 in range(200):  # 250 -1
            dat = self.single_shoot_data(iso, five_ms)
            #data = improc.data2rgb(dat)
            datafileName = '%s_df.data' % str(i0 + 1)
            with open(DARKFRAMES_5MS + "/" + datafileName, 'wb') as g:
                dat.tofile(g)

        for i0 in range(200): # 250 -1
            dat = self.single_shoot_data(iso,fity_ms)
            #data = improc.data2rgb(dat)
            datafileName = '%s_df.data' % str(i0 + 1)
            with open(DARKFRAMES_50MS + "/" + datafileName, 'wb') as g:
                dat.tofile(g)

        logger.info('All dark frames taken.')
        print('All dark frame pictures taken')

    def take_whiteframe_pictures(self, with_jpg):
        helper = Helpers()
        s = Logger()
        logger = s.getLogger()
        imprc = Imgproc()

        five_ms =  5 * 1000   # shutterspeed is in units of microseconds
        fity_ms = 50 * 1000
        iso = 100

        helper.createNewFolder(WHITEFRAMES_5MS)
        helper.createNewFolder(WHITEFRAMES_50MS)
        legend = 'WF 5ms: {df_name}: mean: {df_mean}, median: {df_medi}, std: {df_stdv}, var: {df_var}'

        for i0 in range(200-1):  # 250 -1
            dat = self.single_shoot_data(iso, five_ms)
            datafileName = '%s_wf.data' % str(i0 + 1)

            stats = dict(
                df_name = '{}'.format(datafileName.strip('.data').split('/')[-1]),
                df_mean = '{0:.2f}'.format(np.mean(dat)),
                df_medi = '{0:.2f}'.format(np.median(dat)),
                df_stdv = '{0:.2f}'.format(np.std(dat)),
                df_var  = '{0:.2f}'.format(np.var(dat)),
            )
            print(legend.format(**stats))

            if with_jpg:
                wf_name = '{}_wf5ms.jpg'.format(i0 + 1)
                img = imprc.demosaic1(dat.astype('uint16'))
                wf = imprc.toRGB_1(img)
                cv2.imwrite(join(WHITEFRAMES_5MS, wf_name), wf)

            with open(WHITEFRAMES_5MS + "/" + datafileName, 'wb') as g:
                dat.tofile(g)

        legend = 'WF 50ms: {df_name}: mean: {df_mean}, median: {df_medi}, std: {df_stdv}, var: {df_var}'
        for i0 in range(200-1): # 250 -1
            dat = self.single_shoot_data(iso,fity_ms)
            datafileName = '%s_wf.data' % str(i0 + 1)

            stats = dict(
                df_name = '{}'.format(datafileName.strip('.data').split('/')[-1]),
                df_mean = '{0:.2f}'.format(np.mean(dat)),
                df_medi = '{0:.2f}'.format(np.median(dat)),
                df_stdv = '{0:.2f}'.format(np.std(dat)),
                df_var  = '{0:.2f}'.format(np.var(dat)),
            )
            print(legend.format(**stats))

            if with_jpg:
                wf_name = '{}_wf50ms.jpg'.format(i0 + 1)
                img = imprc.demosaic1(dat.astype('uint16'))
                wf = imprc.toRGB_1(img)
                cv2.imwrite(join(WHITEFRAMES_50MS, wf_name), wf)

            with open(WHITEFRAMES_50MS+ "/" + datafileName, 'wb') as g:
                dat.tofile(g)

        logger.info('All white frames taken.')
        print('All white frames taken')

def main():
    try:
        cfg = {
            'camera_ID': 0,
            'w': 2592,
            'h': 1944,
            'iso': 100,
        }

        s = Logger()
        log = s.getLogger()
        helper = Helpers()
        helper.createNewFolder(RADIOMETRICALIB)
        imprc = Imgproc()

        take_whiteframes = False
        take_darkframes  = False

        if sys.platform == "linux":
            picam = picamera.PiCamera()
            camera = Camera(picam,Camera_config(cfg))
            camera.warm_up()

            if take_darkframes:
                camera.take_darkframe_pictures()

            if take_whiteframes:
                camera.take_whiteframe_pictures(True)

        # imprc.plot_data_histogram(DATAPATH)


        imprc.average_darkframes()
        # imprc.average_whiteframes()


        cb = Color_Balance()
        out = cb.simplest_cb('/home/pi/python_scripts/picam/radiometric/df_avg50ms.data',1)
        jpg = cv2.imread('/home/pi/python_scripts/picam/radiometric/df_avg50ms.jpg')
        cv2.imshow("before", jpg)
        cv2.imshow("after", out)
        cv2.imwrite('/home/pi/python_scripts/picam/radiometric/df_avg50ms_wb.jpg',out)
        cv2.waitKey(0)


        #data = np.fromfile(DATAPATH, dtype='uint16')
        #imprc.average_darkframes()
        #df_avg5ms = np.fromfile(DF_AVG5MS, dtype='uint16')
        #flatfield = imprc.demosaic1(df_avg5ms)
        #flatfield  = imprc.create_flatfield()
        #image = imprc.toRGB_1(flatfield)
        #cv2.imwrite(join(RADIOMETRICALIB, "flatfield.jpg"), image)
        #print('Flat Field image: {}'.format(join(RADIOMETRICALIB, "flatfield.jpg")))


        #df_subtracted  = imprc.substract_darkframes(data)


    except Exception as e:
        if sys.platform == "linux": picam.close()
        log.error(' MAIN: Error in main: ' + str(e))


if __name__ == '__main__':
    main()