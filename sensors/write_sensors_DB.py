#!/usr/bin/env python
import sqlite3
import os
import sys
import stat
import fcntl
import tempfile
import logging
import logging.handlers
from time import sleep
from datetime import datetime
from os.path import basename
import pwd
import grp
import temperature
import infrared
import lux
import rgb
import time

######################################################################
## Hoa: 13.04.2018 Version 4 : write_sensors_DB.py
######################################################################
# This class collects all sensor data and writes them to a SQL database.
# Script must be called each minute by cronjob.
#
# New /Changes:
# ----------------------------------------------------------------------
#
# 09.11.2017 : implemented
# 21.12.2017 : Added Camera_id (Camera 1 - 3) must be set accordingly
# 31.12.2017 : New, run endless at boot up
# 31.12.2017 : Added skipping sensors if they are faulty
# 13.04.2018 : Script runs new as singleton
#
######################################################################

# global variables
global SCRIPTPATH
global ERRFILEPATH
global DB_NAME
global DB_CON
global DB_PATH
global CAMERA_ID

global skip_MLX, cnt_skip_MLX
global skip_LUX, cnt_skip_LUX
global skip_RGB, cnt_skip_RGB
global max_skips

# initial variable values
skip_MLX = False
skip_LUX = False
skip_RGB = False
cnt_skip_MLX = 0
cnt_skip_LUX = 0
cnt_skip_RGB = 0
max_skips = 10

CAMERA_ID = 1 # Location: @ roof top of Trakt IV LU Horw

DB_NAME = 'sensor_DB' + '.db'

SCRIPTPATH  = os.path.join('/home', 'pi', 'python_scripts', 'sensors')
ERRFILEPATH = os.path.join(SCRIPTPATH, 'write_sensor.log')
DB_PATH     = os.path.join(SCRIPTPATH, DB_NAME)


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

class DB_handler:
    
    def createDB(self):
        global DB_NAME
        global DB_CON
        global DB_PATH
        success = False

        try:
            s = Logger()
            root_logger = s.getLogger()
            DB_CON = open(DB_PATH, 'r+')
            DB_CON = sqlite3.connect(DB_PATH)
            self.create_SensorData_table()
            #root_logger.info(' DB  : Found existing DB at program startup')
            setOwnerAndPermission(DB_PATH)
            success = True
            return success

        except IOError as e:
            if e.args[0] == 2:  # No such file or directory -> as expected(!)
                DB_CON = sqlite3.connect(DB_PATH)
                setOwnerAndPermission(DB_PATH)
                self.create_SensorData_table()
                success = True
                root_logger.info(' DB: Created new DB: ' + str(DB_NAME.replace("/", "")))
                return success

            else:  # permission denied or something else?
                file_state = os.stat(DB_PATH)  # get file permissions
                permission = oct(file_state.st_mode)
                root_logger.error(' DB: Error creating new DB at startup: ' + str(DB_NAME) + str(e))
                root_logger.error(' DB: DB Permission when Error occured: ' + permission)
                return success

    def create_SensorData_table(self):
        try:
            global DB_CON
            s = Logger()
            root_logger = s.getLogger()
            #root_logger.info('  DB: Table senor_data created')
            curs = DB_CON.cursor()
            curs.execute("""CREATE TABLE IF NOT EXISTS sensor_data
                 (
                    Camera_id text,
                    Timestamp text,
                    DS18B_Dome_Temp text,
                    DS18B_Ambi_Temp text,
                    MLX_Ambi_Temp text,
                    MLX_Obj_Temp text,
                    TSL_Full_Spec text,
                    TSL_Infra_Spec text,
                    TSL_Visib_Spec text,
                    TCS_RED text,
                    TCS_GREEN text,
                    TCS_BLUE text,
                    Uploaded                    
                  )
               """)
        except Exception as e:
            root_logger.error('DB  : Error creating MeterRealtime Table: ' + str(e))

    def update_all_senors(self,
                                    Camera_id,
                                    Timestamp,
                                    DS18B_Dome_Temp,
                                    DS18B_Ambi_Temp,
                                    MLX_Ambi_Temp,
                                    MLX_Obj_Temp,
                                    TSL_Full_Spec,
                                    TSL_Infra_Spec,
                                    TSL_Visib_Spec,
                                    TCS_RED,
                                    TCS_GREEN,
                                    TCS_BLUE,
                                    Uploaded):
                                           
        try:
            global DB_CON
            s = Logger()
            root_logger = s.getLogger()
            curs = DB_CON.cursor()
            curs.execute("INSERT INTO sensor_data"
                         "("
                         "Camera_id,"
                         "Timestamp,"
                         "DS18B_Dome_Temp,"
                         "DS18B_Ambi_Temp," 
                         "MLX_Ambi_Temp,"
                         "MLX_Obj_Temp,"
                         "TSL_Full_Spec,"
                         "TSL_Infra_Spec,"
                         "TSL_Visib_Spec,"
                         "TCS_RED,"
                         "TCS_GREEN,"
                         "TCS_BLUE,"
                         "Uploaded"                   

                         ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (
                             Camera_id,
                             Timestamp,
                             DS18B_Dome_Temp,
                             DS18B_Ambi_Temp,
                             MLX_Ambi_Temp,
                             MLX_Obj_Temp,
                             TSL_Full_Spec,
                             TSL_Infra_Spec,
                             TSL_Visib_Spec,
                             TCS_RED,
                             TCS_GREEN,
                             TCS_BLUE,
                             Uploaded
                         )
                         )
            DB_CON.commit()
        except Exception as e:
            root_logger.error(' DB: Error while updating senor_data Table: ' + str(e))

        finally:
            DB_CON.commit()
            
    
    def closeDB(self):
        try:
            global DB_CON
            DB_CON.commit()
            DB_CON.close()

        except Exception as e:
            return

    def get_all_sensor_data(self):
        global skip_MLX, cnt_skip_MLX
        global skip_LUX, cnt_skip_LUX
        global skip_RGB, cnt_skip_RGB
        global max_skips

        Timestamp = datetime.now().strftime('%Y %m %d - %H:%M:%S')

        s = Logger()
        root_logger = s.getLogger()

        try:
            sensor = 'DS18B'
            DS18B = temperature.DS18B20()
            DS18B_Dome_Temp     = DS18B.get_cameradome_temp()
            DS18B_Ambi_Temp     = DS18B.get_ambient_temp()

            sleep(3)

            if not skip_MLX:
                sensor = 'MLX'
                MLX = infrared.MLX90614()
                MLX_Ambi_Temp       = MLX.get_amb_temp()
                MLX_Obj_Temp        = MLX.get_obj_temp()
                sleep(3)
            else:
                MLX_Ambi_Temp       = '-999'
                MLX_Obj_Temp        = '-999'
                cnt_skip_MLX += 1
                
                if cnt_skip_MLX >= max_skips:
                    skip_MLX = False
                    cnt_skip_MLX = 0          
                
            if not skip_LUX:
                sensor = 'LUX'
                TSL = lux.TSL2561()
                TSL_Full_Spec       = TSL.get_full_spectrum()
                TSL_Infra_Spec      = TSL.get_infrared()
                TSL_Visib_Spec      = TSL.get_visible_spectrum()
                sleep(3)
            else:
                TSL_Full_Spec       = '-999'
                TSL_Infra_Spec      = '-999'
                TSL_Visib_Spec      = '-999'
                cnt_skip_LUX += 1

                if cnt_skip_LUX >= max_skips:
                    skip_LUX = False
                    cnt_skip_LUX = 0    

            if not skip_RGB:
                sensor = 'RGB'
                TCS = rgb.TCS34725()
                TCS_R,TCS_G,TCS_B   = TCS.get_RGB()
            else:
                TCS_R               = '-999'
                TCS_G               = '-999'
                TCS_B               = '-999'
                cnt_skip_RGB += 1

                if cnt_skip_RGB >= max_skips:
                    skip_RGB = False
                    cnt_skip_RGB = 0
   

            self.update_all_senors(
                CAMERA_ID,
                Timestamp,
                DS18B_Dome_Temp,
                DS18B_Ambi_Temp,
                MLX_Ambi_Temp,
                MLX_Obj_Temp,
                TSL_Full_Spec,
                TSL_Infra_Spec,
                TSL_Visib_Spec,
                TCS_R,
                TCS_G,
                TCS_B,
                Uploaded = '0'
            )            
        except Exception as e:

            if sensor == 'MLX':
                skip_MLX = True
     
            if sensor == 'LUX':
                skip_LUX = True
   
            if sensor == 'RGB':
                skip_RGB = True
                
            root_logger.error(': {0} - SENSOR: '.format(sensor) + str(e))


    def eraseDB(self):
        global path

        try:
            s = Logger()
            root_logger = s.getLogger()

            test = os.listdir(path)

            for item in test:
                if item.endswith(".db"):
                    os.remove(os.path.join(path, item))

                    root_logger.info(' CLR : Old db erased')

        except Exception as e:
            root_logger.error('CLR : Could not erase old database: ' + str(e))
            
def do_Sensor_Data_Logging():
    try:
        s = Logger()
        root_logger = s.getLogger()

        data = DB_handler()
        success = data.createDB()
        data.get_all_sensor_data()

        if success:
            return
        else:
            root_logger.error('DATA: Could not create SQL database.')

    except Exception as e:
        root_logger.error(': do_Sensor_Data_Logging() -> ' + str(e))

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

def ensure_single_instance_of_app():
    app_name = 'write_sensors_DB'  # app name to be monitored

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

def main():
    try:
        s = Logger()
        root_logger = s.getLogger()
        ensure_single_instance_of_app()
        do_Sensor_Data_Logging()

    except Exception as e:
        root_logger.error('MAIN: Error: ' + str(e))


if __name__ == '__main__':
    main()
