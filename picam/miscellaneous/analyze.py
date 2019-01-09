#!/usr/bin/env python

from __future__ import print_function

import os
import cv2
import sys
import time
import shutil
import exifread
from shutil import copy2
from glob import glob
import subprocess
import zipfile
from matplotlib import pyplot as plt
from os import listdir
from os.path import isfile, join
import numpy as np
from fractions import Fraction

print('Version opencv: ' + cv2.__version__)

######################################################################
## Hoa: 07.10.2018 Version 1 : analyze.py
######################################################################
# Reads pictures and plots their histograms
#
#
#
# New /Changes:
# ----------------------------------------------------------------------
#
# 29.09.2018 : first implemented
# 03.10.2018 : using a mask for histogram
#
######################################################################
global Path_to_sourceDir
global Avoid_This_Directories
global Path_to_copy_imgs
global mask_images
global listOfAvgBrightness
global intervall # sets slide show speed

Avoid_This_Directories = ['wellExp','hdr','img2analyze']
Path_to_sourceDir = r'I:\SkY_CAM_IMGS\picam\camera_3\20181007'  # test' picam_pictures
Path_to_copy_imgs = os.path.join(Path_to_sourceDir, 'img2analyze')
intervall = 0.5
mask_images = False


class Helpers:
    def cmask(self, index, radius, array):
        """Generates the mask for a given input image.
        The generated mask is needed to remove occlusions during post-processing steps.

        Args:
            index (numpy array): Array containing the x- and y- co-ordinate of the center of the circular mask.
            radius (float): Radius of the circular mask.
            array (numpy array): Input sky/cloud image for which the mask is generated.

        Returns:
            numpy array: Generated mask image."""

        a, b = index
        is_rgb = len(array.shape)

        if is_rgb == 3:
            ash = array.shape
            nx = ash[0]
            ny = ash[1]
        else:
            nx, ny = array.shape

        s = (nx, ny)
        image_mask = np.zeros(s)
        y, x = np.ogrid[-a:nx - a, -b:ny - b]
        mask = x * x + y * y <= radius * radius
        image_mask[mask] = 1

        return (image_mask)

    def maske_image(self, input_image, size=[1944, 2592, 3], centre=[972, 1296], radius=1350):  # 880,1190, r = 1450

        empty_img = np.zeros(size, dtype=np.uint8)
        mask = self.cmask(centre, radius, empty_img)

        red = input_image[:, :, 0]
        green = input_image[:, :, 1]
        blue = input_image[:, :, 2]

        r_img = red.astype(float) * mask
        g_img = green.astype(float) * mask
        b_img = blue.astype(float) * mask

        dimension = (input_image.shape[0], input_image.shape[1], 3)
        output_img = np.zeros(dimension, dtype=np.uint8)

        output_img[..., 0] = r_img[:, :]
        output_img[..., 1] = g_img[:, :]
        output_img[..., 2] = b_img[:, :]

        return output_img

    def find_centre(self,image,mask):
        # find biggest cont
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        # find largest contour in mask, use to compute minEnCircle
        c = max(contours, key=cv2.contourArea)
        cv2.drawContours(image, c, -1, (255, 255, 255), 3)

        # get center of detected circle
        moments = cv2.moments(c)
        cx = int(moments['m10'] / moments['m00'])
        cy = int(moments['m01'] / moments['m00'])

        return [cx,cy]

    def draw_radius(selfself,image,mask, cx=0,cy=0):

        localIndex = 0
        ##move from the center until we hit white

        while (mask[cx, cy + localIndex] == 0):
            cv2.line(img=image, pt1=(cx, cy), pt2=(cx, cy + localIndex), color=(0, 255, 255),thickness=3)
            localIndex = localIndex + 1
            print(mask[cx, cy + localIndex])

        cv2.imshow("linedImage", image)
        cv2.waitKey(0)

        return image

    def getDirectories(self,pathToDirectories):
        try:
            global Avoid_This_Directories
            allDirs = []
            img_cnt = 1

            for dirs in sorted(glob(os.path.join(pathToDirectories, "*", ""))):
                if os.path.isdir(dirs):
                    if dirs.rstrip('\\').rpartition('\\')[-1] not in Avoid_This_Directories:
                        allDirs.append(dirs)
                        #print('{}'.format(str(dirs)))
                        img_cnt +=1

            print('All images loaded! - Found {} images.'.format(img_cnt))

            return allDirs

        except Exception as e:
            print('getDirectories: Error: ' + str(e))

    def loadImages(self, mypath):
        try:
            onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f)) & f.endswith('.jpg')]
            image_stack = np.empty(len(onlyfiles), dtype=object)
            pos = 0
            for n in range(0, len(onlyfiles)):
                img = cv2.imread(join(mypath, onlyfiles[n]), 1)
                image_stack[pos] = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) # convert to show in matplotlib
                pos += 1

            print('Found {} images'.format(str(pos)))

            return image_stack

        except Exception as e:
            print('Error in loadImages: ' + str(e))

    def readAllImages(self,allDirs):
        try:
            global Path_to_sourceDir
            global mask_images
            list_names = []
            list_images = []
            cnt = 1
            print('Converting jpg to opencv, may take some time!')

            t_start = time.time()
            for next_dir in allDirs:
                next_dir += 'raw_img0.jpg'
                img = cv2.imread(next_dir, 1)
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) # convert to show in matplotlib

                if mask_images:
                    width,hight,color = img_rgb.shape
                    masked_img = self.maske_image(np.uint8(img_rgb), [width, hight, color], (616, 824), 1000)
                    img_rgb = masked_img

                list_images.append(img_rgb)

                '''
                new_img = cv2.resize(img_rgb, None, fx=0.25, fy=0.25)
                list_images.append(new_img)
                '''

                cnt += 1

            t_end = time.time()
            measurement = t_end-t_start
            print('Total number of images: {}'.format(cnt))
            print('Time to load and convert imgs: {}'.format(measurement))

            return list_images

        except Exception as e:
            print('Last directory to read: {}'.format(next_dir))
            print('readAllImages: Error: ' + str(e))

    def plotHystogram(self,img,fig,avgb):

        left, bottom, width, height = [0.645, 0.6, 0.35, 0.35]
        ax2 = fig.add_axes([left, bottom, width, height])

        text = ax2.text(80, 15000, r'avgbrg: ' + str(avgb), fontsize=12, color='black')

        '''
        # The same when bin - interval set to [1,255] ignoring zero values and extreme exposure
        aa = img.copy()
        mask = aa.copy()
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        mask[np.where((mask != [0]).all(axis=1))] = [255]
        mask = mask.astype(np.uint8)
        '''

        color = ('b', 'g', 'r')
        for i, col in enumerate(color):
            histr = cv2.calcHist([img], [i], None, [254], [1, 255])
            plt.plot(histr, color=col)
            plt.xlim([0, 256])

        return ax2,text

    def runSlideShow(self, image_list = None, run = True):
        if run:

            font_outer = {'family': 'serif',
                    'color': 'darkred',
                    'weight': 'normal',
                    'size': 12,
                    }

            counter = 0

            fig_outer = plt.gcf() # get access to current figure
            ax_outer = plt.gca()  # get access to current axes
            ax_outer.set_xlabel('[pixel]')
            ax_outer.set_ylabel('[pixel]')

            if len(image_list) == 0:
                print('Error in runSlideShow: Image list is empty !')
                return

            cur_window = ax_outer.imshow(image_list[0])

            while counter < len(image_list):

                next_img = image_list[counter]
                avgb = listOfAvgBrightness[counter]
                ax_outer.set_title('Image: {}'.format(counter))
                #text = ax_outer.text(-10, -20, r'avgbrg: '+str(avgb), fontsize=12,color='black')
                cur_window.set_data(next_img)
                ax2,text = self.plotHystogram(next_img,fig_outer,avgb)

                plt.draw()
                plt.pause(intervall)
                text.remove()
                counter += 1
                ax2.clear()

    def avgbrightness(self, im):
        """
        Find the average brightness of the provided image.

        Args:
          im: A opencv image.
          config: A timelapseConfig object.  Defaults to self.config.
        Returns:
          Average brightness of the image.
        """
        aa = im.copy()
        heigth, width, channels = aa.shape

        if width > 128:
            imRes = cv2.resize(aa, (128, 96), interpolation=cv2.INTER_AREA)
            mask = imRes.copy()
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            mask[np.where((mask != [0]).all(axis=1))] = [255]
            mask = mask.astype(np.uint8)
            aa = cv2.cvtColor(imRes, cv2.COLOR_BGR2GRAY)
        else:
            mask = aa.copy()
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            mask[np.where((mask != [0]).all(axis=1))] = [255]
            mask = mask.astype(np.uint8)
            aa = cv2.cvtColor(aa, cv2.COLOR_BGR2GRAY)

        pixels = (aa.shape[0] * aa.shape[1])
        h = cv2.calcHist([aa], [0], mask, [256], [0, 256])
        mu0 = 1.0 * sum([i * h[i] for i in range(len(h))]) / pixels
        return round(mu0[0], 2)

    def calcAllAvgBrightness(self, listOfAllImages):
        try:
            listOfAllAvgBrightness = []

            for img in listOfAllImages:
                listOfAllAvgBrightness.append(self.avgbrightness(img))

            return listOfAllAvgBrightness

        except Exception as e:
            print('calcAllAvgBrightness: Error: ' + str(e))
            return listOfAllAvgBrightness


def main():
    try:
        global Path_to_sourceDir
        global listOfAvgBrightness
        global intervall
        intervall = 0.3
        preprocess = False  # Collect images from subdirectories

        if not os.path.isdir(Path_to_sourceDir):
            print('\nError: Image directory does not exist! -> Aborting.')
            return;

        help = Helpers()

        if preprocess:
            # OK korrekte Farben
            allDirs = help.getDirectories(Path_to_sourceDir)
            listOfImages = help.readAllImages(allDirs)
        else:
            # All images are allready in one folder
            listOfImages = help.loadImages(join(Path_to_sourceDir,'hdr'))

        listOfAvgBrightness = help.calcAllAvgBrightness(listOfImages)
        help.runSlideShow(listOfImages)

        print('Postprocess.py done')

    except Exception as e:
        print('MAIN: Error in main: ' + str(e))


if __name__ == '__main__':
    main()