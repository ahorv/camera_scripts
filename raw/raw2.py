#!/usr/bin/cd python

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
import shutil
import tempfile
import logging
import logging.handlers
from datetime import datetime, timedelta
import numpy as np

if sys.platform == "linux":
    import pwd
    import grp
    import stat
    import fcntl
    import picamera

######################################################################
## Hoa: 24.09.2018 Version 2 : raw2.py
######################################################################
# This class takes 3 consecutive images with increasing shutter times.
# Pictures are in raw bayer format. In addition a jpg as reference is
# taken.
# Aim is to merge a sequence of images to a HDR image.
# Runtime for a sequence of 3 images is about 21 sec
# Shutter times: img0: 85, img5: 595, img9: 992 micro secs
#
# Start and end time, are set here inside the script ! Script is run
# by a cronjob.
#
# New /Changes:
# ----------------------------------------------------------------------
#
# 10.11.2017 : Added new logging
# 25.03.2018 : new version only 3 shutter times
# 31.03.2018 : added single instance functionality by a lock file
# 02.04.2018 : Logging to multiple files
# 24.09.2018 : Changed description in header
#
######################################################################

global SCRIPTPATH
global RAWDATAPATH
global SUBDIRPATH
global CAMERA

CAMERA = 'camera_1'
SCRIPTPATH = os.path.join('/home', 'pi', 'python_scripts', 'raw')
RAWDATAPATH = os.path.join(SCRIPTPATH, 'raw_data')


class Logger:
    def __init__(self):
        self.logger = None

    def getLogger(self, newLogPath=None):

        try:
            global SCRIPTPATH

            if newLogPath is None:
                LOGFILEPATH = os.path.join(SCRIPTPATH, 'raw2.log')
                logFormatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
                fileHandler = logging.FileHandler(LOGFILEPATH)
                name = 'rootlogger'
            else:
                LOGFILEPATH = newLogPath
                logFormatter = logging.Formatter('%(message)s')
                fileHandler = logging.FileHandler(LOGFILEPATH)
                name = 'camstatslogger'

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


class Rawcamera:
    def takepictures(self):
        try:

            global SUBDIRPATH
            global CAMERA

            h = Helpers()
            camLogPath = h.createNewRawFolder()
            s = Logger()
            cameralog = s.getLogger(camLogPath)
            cameralog.info('{}: {}'.format(CAMERA, datetime.now().strftime('%Y%m%d_%H%M%S')))

            stream = io.BytesIO()
            with picamera.PiCamera() as camera:
                camera.resolution = (2592, 1944)
                # shutter speed is limited by framerate!
                camera.framerate = 1
                camera.exposure_mode = 'off'
                camera.awb_mode = 'auto'
                camera.iso = 0
                shutter_speed = 100
                # for i0 in range(10):
                for i0 in [0, 5, 9]:
                    # set shutter speed
                    loopstart_tot = time.time()
                    camera.shutter_speed = (i0 + 1) * shutter_speed
                    fileName = 'raw_img%s.jpg' % str(i0)

                    # Capture the image, without the Bayer data to file
                    loopstartjpg = time.time()
                    camera.capture(SUBDIRPATH + "/" + fileName, format='jpeg', bayer=False)
                    loopendjpg = time.time()

                    # Capture the image, including the Bayer data to stream
                    loopstartraw = time.time()
                    camera.capture(stream, format='jpeg', bayer=True)
                    loopendraw = time.time()

                    data = stream.getvalue()[-10270208:]
                    data = data[32768:4128 * 2480 + 32768]
                    data = np.fromstring(data, dtype=np.uint8)
                    data = data.reshape((2480, 4128))[:2464, :4120]
                    data = data.astype(np.uint16) << 2
                    for byte in range(4):
                        data[:, byte::5] |= ((data[:, 4::5] >> ((4 - byte) * 2)) & 0b11)

                    data = np.delete(data, np.s_[4::5], 1)

                    loopend_tot = time.time()
                    # camera settings
                    cam_stats = dict(
                        ss=camera.shutter_speed,
                        iso=camera.iso,
                        exp=camera.exposure_speed,
                        ag=camera.analog_gain,
                        dg=camera.digital_gain,
                        awb=camera.awb_gains,
                        br=camera.brightness,
                        ct=camera.contrast,
                    )
                    t_stats = dict(
                        t_jpg='{0:.2f}'.format(loopendjpg - loopstartjpg),
                        t_raw='{0:.2f}'.format(loopendraw - loopstartraw),
                        t_tot='{0:.2f}'.format(loopend_tot - loopstart_tot),
                    )

                    # Write camera settings to log file
                    logdata = '{} Run :'.format(str(i0))
                    logdata = logdata + ' [ss:{ss}, iso:{iso} exp:{exp}, ag:{ag}, dg:{dg}, awb:[{awb}], br:{br}, ct:{ct}]'.format(
                        **cam_stats)
                    logdata = logdata + ' || timing: [t_jpg:{t_jpg}, t_raw:{t_raw}, t_tot:{t_tot}]'.format(**t_stats)

                    cameralog.info(logdata)

                    # Finally save raw (16bit data) having a size 3296 x 2464
                    datafileName = 'data%d_%s.data' % (i0, str(''))

                    with open(SUBDIRPATH + "/" + datafileName, 'wb') as g:
                        data.tofile(g)

                s.closeLogHandler()

        except Exception as e:
            camera.close()
            print('Error in takepicture: ' + str(e))


class Helpers:
    def ensure_single_instance_of_app(self):
        app_name = 'raw2'  # app name to be monitored

        if sys.platform == "linux":

            # Establish lock file settings
            lf_name = '.{}.lock'.format(app_name)
            lf_path = os.path.join(tempfile.gettempdir(), lf_name)
            lf_flags = os.O_WRONLY | os.O_CREAT
            lf_mode = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH  # This is 0o222, i.e. 146

            # Create lock file
            # Regarding umask, see https://stackoverflow.com/a/15015748/832230
            umask_original = os.umask(0)
            try:
                lf_fd = os.open(lf_path, lf_flags, lf_mode)
            finally:
                os.umask(umask_original)

            # Try locking the file
            try:
                fcntl.lockf(lf_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError as e:
                msg = ('{} may already be running. Only one instance of it '
                       'allowed.'
                       ).format('raw2')
                print(' LOCK: ' + str(msg))
                exit()

    def createNewRawFolder(self):
        try:
            global RAWDATAPATH
            global SUBDIRPATH

            TSTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.createNewFolder(RAWDATAPATH)
            SUBDIRPATH = os.path.join(RAWDATAPATH, TSTAMP)
            self.createNewFolder(SUBDIRPATH)
            camLogPath = os.path.join(SUBDIRPATH, 'camstats.log')

            return camLogPath

        except IOError as e:
            print('PATH: Could not set path and folder: ' + str(e))

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

    def disk_stat(self):

        try:
            global disc_stat_once
            s = Logger()
            log = s.getLogger()

            total, used, free = shutil.disk_usage("/usr")
            total_space = total / 1073741824
            used_space = used / 1073741824
            free_space = free / 1073741824

            disc_status = 'Disc Size:%iGB\tSpace used:%iGB\tFree space:%iGB ' % (total_space, used_space, free_space)
            log.info(disc_status)
            percent = used_space / (total_space / 100)

            return percent

        except IOError as e:
            print('DISKSTAT :  ' + str(e))

    def str2time(self, time_as_str):

        try:
            now = datetime.now()
            year = str(now.year)
            month = str(now.month)
            day = str(now.day)
            temp = year + '-' + month + '-' + day + '_' + time_as_str
            str_as_time = datetime.strptime(temp, '%Y-%m-%d_%H:%M:%S')

            return str_as_time

        except Exception as e:
            print('str2time: ' + str(e))


def main():
    try:
        helper = Helpers()
        usedspace = helper.disk_stat()
        helper.ensure_single_instance_of_app()
        s = Logger()
        log = s.getLogger()

        if usedspace > 80:
            raise RuntimeError('WARNING: Not enough free space on SD Card!')
            return

        cam = Rawcamera()

        time_start = '9:00:00'  # Start time of time laps
        time_end = '15:00:00'  # Stop  time of time laps

        t_start = helper.str2time(time_start)
        t_end = helper.str2time(time_end)

        while (True):
            time_now = datetime.now().replace(microsecond=0)

            if t_start < time_now < t_end:
                cam.takepictures()

            elif t_end > time_now or t_start < time_now:
                sys.exit()


    except Exception as e:
        log.error(' MAIN: Error in main: ' + str(e))


if __name__ == '__main__':
    main()
