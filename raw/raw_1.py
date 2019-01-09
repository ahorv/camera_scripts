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
import time
import pwd
import grp
import picamera
import zipfile
import shutil
import logging
import logging.handlers
from datetime import datetime
import numpy as np


######################################################################
## Hoa: 09.11.2017 Version 4 : raw.py
######################################################################
# This class takes 10 consecutive images with increasing shutter times.
# Pictures are in raw bayer format. In addition a jpg is taken as
# reference.
#
# Aim is to merge a sequence of images to a HDR image.
#
# Remarks: On run takes 2'30''-> therefore cronjob interval must be > 2'30''
#
# New /Changes:
# ----------------------------------------------------------------------
#
# 10.11.2017 : Added new logging
#
#
######################################################################

global RAWDATAPATH
global LOGFILEPATH
global SUBDIRPATH
global TSTAMP


class Logger:
    def getLogger(self):

        try:
            global LOGFILEPATH

            # configure log formatter
            #logFormatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
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

class Rawcamera:

    def takepictures(self):
        try:

            global SUBDIRPATH

            s = Logger()
            log = s.getLogger()

            stream = io.BytesIO()
            with picamera.PiCamera() as camera:
                # Let the camera warm up for a couple of seconds
                camera.resolution = (2592, 1944)
                # 1/2 per second
                # camera.framerate = Fraction(1, 2)
                # shutter speed is limited by framerate!
                camera.framerate = 1
                camera.exposure_mode = 'off'
                camera.awb_mode = 'auto'
                camera.iso = 0
                shutter_speed = 100
                for i0 in range(10):
                    # set shutter speed
                    camera.shutter_speed = (i0 + 1) * shutter_speed
                    # time.sleep(2)
                    fileName = 'raw_img%s.jpg' % str(i0)
                    # Capture the image, without the Bayer data to file
                    camera.capture(SUBDIRPATH + "/" + fileName, format='jpeg', bayer=False)

                    # Capture the image, including the Bayer data to stream
                    camera.capture(stream, format='jpeg', bayer=True)

                    # camera settings
                    exp = camera.exposure_speed
                    ag = camera.analog_gain
                    dg = camera.digital_gain
                    awb = camera.awb_gains
                    br = camera.brightness
                    ct = camera.contrast

                    logdata = '{} Run: camera shutter speed:[{}] '.format(str(i0),camera.shutter_speed)
                    logdata = logdata +'| camera settings: [exposure time'
                    logdata = logdata +' %d, ag %f, dg %f, awb %s, br %d, ct = %d]' % (exp, ag, dg, str(awb), br, ct)

                    log.info(logdata)

                    # Extract the raw Bayer data from the end of the stream (is in jpeg-meta data), check the
                    # header and strip it off before converting the data into a numpy array

                    data = stream.getvalue()[-10270208:]
                    # print('%s' % data[:4])
                    # assert data[:4] == 'BRCM'
                    data = data[32768:4128 * 2480 + 32768]
                    data = np.fromstring(data, dtype=np.uint8)

                    # The data consists of 2480 rows of 4128 bytes of data. The last rows
                    # of data are unused (they only exist because the actual resolution of
                    # is rounded up to the nearest 16). Likewise, the last
                    # bytes of each row are unused (why?). Here we reshape the data and
                    # strip off the unused bytes

                    data = data.reshape((2480, 4128))[:2464, :4120]

                    # Horizontally, each row consists of 4120 10-bit values. Every four
                    # bytes are the high 8-bits of four values, and the 5th byte contains
                    # the packed low 2-bits of the preceding four values. In other words,
                    # the bits of the values A, B, C, D and arranged like so:
                    #
                    #  byte 1   byte 2   byte 3   byte 4   byte 5
                    # AAAAAAAA BBBBBBBB CCCCCCCC DDDDDDDD AABBCCDD
                    #
                    # Here, we convert our data into a 16-bit array, shift all values left
                    # by 2-bits and unpack the low-order bits from every 5th byte in each
                    # row, then remove the columns containing the packed bits

                    data = data.astype(np.uint16) << 2
                    for byte in range(4):
                        data[:, byte::5] |= ((data[:, 4::5] >> ((4 - byte) * 2)) & 0b11)

                    data = np.delete(data, np.s_[4::5], 1)

                    # Finally save raw (16bit data) having a size 3296 x 2464
                    datafileName = 'data%d_%s.data' % (i0, str(''))
                    #print('%s' % fileName)
                    with open(SUBDIRPATH + "/" + datafileName, 'wb') as g:
                        data.tofile(g)

        except Exception as e:
            camera.close()
            print('Error in takepicture: ' + str(e))

class Helpers:

    def setPathAndNewFolders(self):
        try:
            global RAWDATAPATH
            global LOGFILEPATH
            global SUBDIRPATH
            global TSTAMP

            TSTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')

            RAWDATAPATH = os.path.join('/home', 'pi', 'python_scripts', 'raw', 'raw_data')
            self.createNewFolder(RAWDATAPATH)
            SUBDIRPATH = os.path.join(RAWDATAPATH, TSTAMP)
            self.createNewFolder(SUBDIRPATH)
            LOGFILEPATH = os.path.join(SUBDIRPATH, TSTAMP + '_raw' + '.log')

        except IOError as e:
            print('PATH: Could not set path and folder: ' + str(e))

    def createNewFolder(self,thispath):
        try:
            if not os.path.exists(thispath):
                os.makedirs(thispath)
                self.setOwnerAndPermission(thispath)

        except IOError as e:
            print('DIR : Could not create new folder: ' + str(e))

    def setOwnerAndPermission(self,pathToFile):
        try:
            uid = pwd.getpwnam('pi').pw_uid
            gid = grp.getgrnam('pi').gr_gid
            os.chown(pathToFile, uid, gid)
            os.chmod(pathToFile, 0o777)
        except IOError as e:
            print('PERM : Could not set permissions for file: ' + str(e))

    def zipitall(self):
        try:
            global RAWDATAPATH
            dirtozip = ''
            for nextdir, subdirs, files in os.walk(RAWDATAPATH + "/"):
                newzipname = nextdir.split('/')[-1]
                if newzipname:

                    dirtozip    = os.path.join(RAWDATAPATH,newzipname)
                    zipfilepath = os.path.join(RAWDATAPATH,newzipname)

                    zf = zipfile.ZipFile(zipfilepath+'.zip', "w")
                    for dirname, subdirs, files in os.walk(dirtozip):
                        for filename in files:
                            zf.write(os.path.join(dirname, filename), filename, compress_type = zipfile.ZIP_DEFLATED)
                    zf.close()

                    #remove obsolete directory
                    shutil.rmtree(dirtozip, ignore_errors=True)


        except IOError as e:
            print('ZIPALL : Could not create *.zip file: ' + str(e))

    def disk_stat(self):

        try:
            s = Logger()
            log = s.getLogger()

            total, used, free = shutil.disk_usage("/usr")
            total_space = total / 1073741824
            used_space = used / 1073741824
            free_space = free / 1073741824
            disc_status = 'Disc Size:%iGB\nSpace used:%iGB\nFree space:%iGB '% (total_space,used_space,free_space )
            log.info(disc_status)
            percent = used_space/(total_space/100)

            return percent

        except IOError as e:
            print('DISKSTAT :  '+ str(e))

def main():
    try:

        helper = Helpers()
        helper.setPathAndNewFolders()

        usedspace = helper.disk_stat()
        if usedspace > 80:
            raise RuntimeError('WARNING: Not enough free space on SD Card!')
            return

        cam = Rawcamera()
        cam.takepictures()
        helper.zipitall()

    except Exception as e:
        print('Error in Main: ' + str(e))


if __name__ == '__main__':
    main()

