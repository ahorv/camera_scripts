#!/usr/bin/env python
import os
import sys
import logging
import logging.handlers
from ftplib import FTP, error_perm
from glob import glob

#########################################################################
##  23.11.2017 Version 2 : rawexporter.py
#########################################################################
# Exports rawpictures (zipfolder with raw pictures) to the ihomelab ftp.
# All .*zip send to ftp-server will be deleted after sending !
# ftp addr: ftp.ihomelab.ch / resolved: 147.88.219.198:21
# Path to directory on the ftp server: /camera_2/raw/
#
# NEW:
# -----
# - new directory for each day
# - added variable to distinguish between cameras (must be set accordingly !)
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
    ZIPDIRPATH = os.path.join('/home', 'pi','python_scripts','raw', 'raw_data') 
else:
    SCRIPTPATH = os.path.realpath(__file__)
    ERRFILEPATH = os.path.join(SCRIPTPATH, 'rawexporter.log')
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
            s = Logger()
            root_logger = s.getLogger()

            e = Exporter()

            allzipfiles = e.grabAllRawZip()
            uploadedzip = []
            cnt = 0

            zipfilename = allzipfiles[0]
            token = str(zipfilename.split('/')[-1])
            newDirName = str(token.split('_', 1)[0])
            print('New Dir Name: '+ newDirName)
            ftpPath = '/'+CAMERA+'/raw/'

            ftp = FTP('ftp.ihomelab.ch')
            ftp.login('tahorvat', '123ihomelab')
            ftp.cwd(ftpPath)

            try:
                ftp.cwd(newDirName)

            except error_perm:
                ftp.mkd(newDirName)
                ftp.cwd(newDirName)

            for zip_file in sorted(allzipfiles):
                zipfilename = zip_file.split('/')[-1]
                cnt = cnt + 1

                with open(zip_file, 'rb') as out:
                    #print('FTP STOR: %s' % ftp.storbinary('STOR ' + zipfilename, out))
                    ftp.storbinary('STOR ' + zipfilename, out)

                uploadedzip.append(zip_file)
                success = True

            ftp.close()

            root_logger.info(' FTP : {} *.zip files uploaded to ftp.ihomelab.ch'.format(cnt))
            e.deleteUploadedZip(uploadedzip)
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

            root_logger.info('DEL : {} *.zip removed '.format(cnt))

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
