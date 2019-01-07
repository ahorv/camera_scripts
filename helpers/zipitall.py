#!/usr/bin/env python
import os
import time
import sys
import zipfile
import logging
import logging.handlers
import shutil
from glob import glob

#########################################################################
##  26.04.2018 Version 1 : zipitall.py
#########################################################################
# Zips all image folders in /raw/raw_data.
# Processed folders will be deleted, leaving zipped files only.
#
# NEW:
# -----
# -
#
#########################################################################

if sys.platform == "linux":
    import pwd
    import grp

global ZIPDIRPATH
global ERRFILEPATH

ERRFILEPATH = os.path.join('/home', 'pi', 'python_scripts', 'helpers', 'rawexporter.log')
ZIPDIRPATH = os.path.join('/home', 'pi', 'python_scripts', 'raw', 'raw_data')

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

def getDirs():
    try:
        global ZIPDIRPATH
        s = Logger()
        root_logger = s.getLogger()
        allDirs = []

        for dirs in sorted(glob(os.path.join(ZIPDIRPATH, "*", ""))):
            if os.path.isdir(dirs):
                allDirs.append(dirs)

        return allDirs

    except Exception as e:
        root_logger.info('GETDIRS: Error: ' + str(e))

def zipitall():
    try:
        global ZIPDIRPATH
        s = Logger()
        root_logger = s.getLogger()

        allDirs = []
        allDirs = getDirs()

        for dirs in allDirs:

            for nextdir, subdirs, files in os.walk(dirs):
                newzipname = nextdir.split('/')[-2]

                if newzipname:

                    zipfilepath = os.path.join(ZIPDIRPATH, newzipname + '.zip')

                    zf = zipfile.ZipFile(zipfilepath, "w")

                    for dirname, subdirs, files in os.walk(dirs):
                        for filename in files:
                            zf.write(os.path.join(dirname, filename), filename, compress_type=zipfile.ZIP_DEFLATED)

                    zf.close()

                    # delete zipped directory
                    shutil.rmtree(dirs, ignore_errors=True)

    except IOError as e:
        root_logger.error('ZIPALL :Error: ' + str(e))


def main():
    try:
        s = Logger()
        root_logger = s.getLogger()
        root_logger.info('ZIPITALL: STARTED')

        time_to_zip_start = time.time()
        zipitall()
        time_to_zip_end = time.time()
        time_to_zip = time_to_zip_end - time_to_zip_start
        root_logger.info('Time to zip all files: {}'.format(round(time_to_zip, 1)))

    except Exception as e:
        root_logger.error('MAIN: Error: ' + str(e))


if __name__ == '__main__':
    main()
