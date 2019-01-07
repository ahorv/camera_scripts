#!/usr/bin/env python
import os
import sys
import time
import logging
import logging.handlers
from ftplib import FTP, error_perm
from glob import glob

#########################################################################
##  06.04.2018 Version 1 : ftpexporter.py
#########################################################################
# Collects all zip files in raw/raw_data/ and sends them via ftp to
# the ihomelab ftp server.
#
# ftp addr: ftp.ihomelab.ch / resolved: 147.88.219.198:21
# Path to directory on the ftp server: /camera_x/raw/
#
# The variable CAMERA has to be set according to the camera in use!
#
# NEW:
# -----
# -
#
#########################################################################


# global variables
global FTPADR
global SCRIPTPATH
global ERRFILEPATH
global ZIPDIRPATH
global CAMERA

CAMERA = 'camera_1'

if sys.platform == "linux":
    import pwd
    import grp

    SCRIPTPATH = os.path.join('/home', 'pi', 'python_scripts', 'helpers')
    ERRFILEPATH = os.path.join(SCRIPTPATH, 'rawexporter.log')
    ZIPDIRPATH = os.path.join('/home', 'pi', 'python_scripts', 'raw', 'raw_data')
else:
    SCRIPTPATH = os.path.realpath(__file__)
    ERRFILEPATH = os.path.join(SCRIPTPATH, 'rawzipexporter.log')
    ZIPDIRPATH = os.path.join(SCRIPTPATH, 'raw_data')


class Logger:
    def getLogger(self):

        try:
            global ERRFILEPATH

            # configure log formatter
            logFormatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

            # configure file handler
            fileHandler = logging.FileHandler(ERRFILEPATH)
            fileHandler.setFormatter(logFormatter)

            # configure stream handler
            consoleHandler = logging.StreamHandler()
            consoleHandler.setFormatter(logFormatter)

            # get the logger instance
            self.logger = logging.getLogger(__name__)

            # set rotating filehandler
            handler = logging.handlers.RotatingFileHandler(ERRFILEPATH, encoding='utf8',
                                                           maxBytes=1024 * 10000, backupCount=1)

            # set the logging level
            self.logger.setLevel(logging.INFO)

            if not len(self.logger.handlers):
                self.logger.addHandler(fileHandler)
                self.logger.addHandler(consoleHandler)
                # self.logger.addHandler(handler)

            setOwnerAndPermission(ERRFILEPATH)
            return self.logger

        except IOError as e:
            print('Error logger:' + str(e))


def setOwnerAndPermission(pathToFile):
    try:
        if sys.platform == "linux":
            uid = pwd.getpwnam('pi').pw_uid
            gid = grp.getgrnam('pi').gr_gid
            os.chown(pathToFile, uid, gid)
            os.chmod(pathToFile, 0o777)
        else:
            return
    except IOError as e:
        print('PERM : Could not set permissions for file: ' + str(e))

class Exporter:

    def grabAllRawZip(self):
        global ZIPDIRPATH
        try:
            s = Logger()
            root_logger = s.getLogger()

            allzipfiles = []

            for file in sorted(glob(ZIPDIRPATH + '/*.zip')):
                allzipfiles.append(file)

            return allzipfiles

        except Exception as e:
            root_logger.error('GRAB: Error: ' + str(e))

    def sendZipToFTP(self):

        success = False

        try:
            uploadedzip = []
            cnt = 0

            s = Logger()
            root_logger = s.getLogger()

            allzipfiles = self.grabAllRawZip()
            zipfilename = allzipfiles[0]
            token = str(zipfilename.split('/')[-1])
            newDirName = str(token.split('_', 1)[0])

            ftpPath = '/' + CAMERA + '/raw/'

            ftp = FTP('ftp.ihomelab.ch')
            ftp.login('tahorvat', '123ihomelab')
            ftp.cwd(ftpPath)

            try:
                ftp.cwd(newDirName)

            except error_perm:
                ftp.mkd(newDirName)
                ftp.cwd(newDirName)

            time_to_send_start = time.time()
            for zip_file in sorted(allzipfiles):
                zipfilename = zip_file.split('/')[-1]
                cnt = cnt + 1

                with open(zip_file, 'rb') as out:
                    ftp.storbinary('STOR ' + zipfilename, out)

                uploadedzip.append(zip_file)
                success = True

            ftp.close()
            time_to_send_end = time.time()
            time_to_send = time_to_send_end-time_to_send_start

            root_logger.info('FTP : {} zip files uploaded in {} sec'.format(cnt, round(time_to_send,1)))
            self.deleteUploadedZip(uploadedzip)
            return success

        except Exception as e:
            root_logger.error('FTP : Error: ' + str(e))
            ftp.quit()
            return False

    def deleteUploadedZip(self, uploadedZipFiles):
        try:
            s = Logger()
            root_logger = s.getLogger()
            cnt = 0

            for zip_file in uploadedZipFiles:
                cnt = cnt + 1
                os.remove(zip_file)
                success = True

            root_logger.info('DEL : {} zip removed '.format(cnt))

            return success

        except Exception as e:
            root_logger.error('DEL : Error: ' + str(e))
            return False


def main():
    try:
        s = Logger()
        root_logger = s.getLogger()
        root_logger.info('Main: UPLOAD STARTED')
        e = Exporter()
        e.sendZipToFTP()

    except Exception as e:
        root_logger.error('MAIN: Error: ' + str(e))


if __name__ == '__main__':
    main()
