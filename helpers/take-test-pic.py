#!/usr/bin/env python

from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
)

import sys
import io
import os
import pwd
import grp
import picamera
import logging
import logging.handlers
from glob import glob
from datetime import datetime

######################################################################
## Hoa: 22.11.2017 Version 1 : taketestPic.py
######################################################################
# Purpos: Takes a picture with picamera. Picture as visual control
# if camera dome is foggy.
#
# Use: run by crontab BEFORE raw.py is executed !
#
# New /Changes:
# ----------------------------------------------------------------------
#
# 22.11.2017 : New
#
#
######################################################################

global TESTPICPATH
global LOGFILEPATH
TESTPICPATH = os.path.join('/home', 'pi', 'python_scripts', 'raw', 'test_pic')
LOGFILEPATH = os.path.join(TESTPICPATH,'testpic.log')


class Logger:
    def getLogger(self):

        try:
            global LOGFILEPATH
            

            # configure log formatter
            # logFormatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            logFormatter = logging.Formatter('%(message)s')

            # configure file handler
            fileHandler = logging.FileHandler(LOGFILEPATH)
            fileHandler.setFormatter(logFormatter)

            # configure stream handler
            consoleHandler = logging.StreamHandler()
            consoleHandler.setFormatter(logFormatter)

            # get the logger instance
            self.logger = logging.getLogger(__name__)

            # set rotating filehandler
            handler = logging.handlers.RotatingFileHandler(LOGFILEPATH, encoding='utf8',
                                                           maxBytes=1024 * 10000, backupCount=1)

            # set the logging level
            self.logger.setLevel(logging.INFO)

            if not len(self.logger.handlers):
                self.logger.addHandler(fileHandler)
                self.logger.addHandler(consoleHandler)
                # self.logger.addHandler(handler)
            helper = Helpers()
            helper.setOwnerAndPermission(LOGFILEPATH)
            return self.logger

        except IOError as e:
            print('Error logger:' + str(e))
            

    def eraseLog(self):
        try:
            global LOGFILEPATH

            f = open(LOGFILEPATH, 'w')
            f.close()            

        except IOError as e:
           print('Error erasing log:' + str(e))


class Testcamera:
    def takepictures(self):
        try:

            global TESTPICPATH

            s = Logger()
            s.eraseLog()
            log = s.getLogger()
     
            h = Helpers()
            

            with picamera.PiCamera() as camera:
                camera.resolution = (2592, 1944)
                camera.framerate = 1
                camera.exposure_mode = 'auto'
                camera.awb_mode = 'auto'

                dateAndTime = datetime.now().strftime('%Y_%m_%d-%H:%M:%S')
                fileName = '%stest_img.jpg' % str(dateAndTime)
                # Capture the image, without the Bayer data to file
                camera.capture(os.path.join(TESTPICPATH,fileName), format='jpeg', bayer=False)

                h.setOwnerAndPermission(TESTPICPATH + "/" + fileName)
                log.info(datetime.now().day)

        except Exception as e:
            camera.close()
            print('Error in takepicture: ' + str(e))


class Helpers:
    def setPathAndNewFolders(self):
        try:
            global TESTPICPATH
            self.createNewFolder(TESTPICPATH)

        except IOError as e:
            print('PATH: Could not set path and folder: ' + str(e))

    def createNewFolder(self, thispath):
        try:
            if not os.path.exists(thispath):
                os.makedirs(thispath)
                self.setOwnerAndPermission(thispath)
            else:
                self.deleteOldPic()

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

    def deleteOldPic(self):
        try:     
            global TESTPICPATH
            global LOGFILEPATH
            
            if not os.path.exists(LOGFILEPATH):
                return

            dt = datetime.now()
            today   = '{:%d}'.format(dt)
            
            with open(LOGFILEPATH,'r') as f:
                line = f.readlines()
                lastday = str(line)
                lastday = lastday.replace('[','')
                lastday = lastday.replace(']','')
                lastday = lastday.replace('\\n','')
                lastday = lastday.replace('\'','')
                lastday = lastday.replace('\'','')         
            
            print('lastday: %s' %lastday)
            print('today: %s' %today)
     
            if (today != lastday):

                for file in sorted(glob(TESTPICPATH + '/*.jpg')):
                    os.remove(file)

                for file in sorted(glob(TESTPICPATH + '/*.log')):
                    os.remove(file)

        except IOError as e:
            print('DEL : Could not delete files: ' + str(e))


def main():
    try:
        helper = Helpers()
        helper.setPathAndNewFolders()
        cam = Testcamera()
        cam.takepictures()

    except Exception as e:
        print('Error in Main: ' + str(e))


if __name__ == '__main__':
    main()
