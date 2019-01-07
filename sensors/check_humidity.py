#!/usr/bin/env python3
import time
import humidity
import RPi.GPIO as GPIO
import sys
import os
import logging
import logging.handlers
from datetime import datetime
import pwd
import grp



######################################################################
## Hoa: 07.01.2018 Version 2 : run_fan.py
######################################################################
# Monitors the humidity in the camera dom. If humidity rises over a
# certain value the fan is run until humidity is fallen under the
# critical humidity value.
#
# New /Changes:
# ----------------------------------------------------------------------
#
# 17.12.2017 : programm is started with the booting of the operating system.
#              (runs for ever)
# 20.12.2017 : Periodic air blast to sens humidity
# 07.01.2018 : Changed reset counter for periodic air blast
#
#
######################################################################

global FAN_GPIO
global MAX_HUMIDITY
global HYST_HUMIDITY
global WRITE_TOLOGG
global COUNTER

FAN_GPIO = 18 # GPIO18 (pin 12)
MAX_HUMIDITY = 55  # Sets value of humidity to start fan
HYST_HUMIDITY = 2
WRITE_TOLOGG = False
COUNTER = 0


class Logger:
    def getLogger(self):

        try:
            SCRIPTPATH = os.path.join('/home', 'pi', 'python_scripts', 'sensors')
            ERRFILEPATH = os.path.join(SCRIPTPATH, 'fan.log')

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

            self.setOwnerAndPermission(ERRFILEPATH)
            return self.logger

        except IOError as e:
            print('Error logger:' + str(e))

    def setOwnerAndPermission(self, pathToFile):
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



def setup():
    global FAN_GPIO
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(FAN_GPIO, GPIO.OUT, initial=0)
    GPIO.output(FAN_GPIO, GPIO.LOW)
    GPIO.setwarnings(False)

def fanON():
    global FAN_GPIO
    GPIO.output(FAN_GPIO, GPIO.HIGH)

def fanOFF():
    global FAN_GPIO
    GPIO.output(FAN_GPIO, GPIO.LOW)

def shortAirBlast(seconds):
    fanON()
    time.sleep(seconds)
    fanOFF()

def check_humidity():
    global WRITE_TOLOGG
    global MAX_HUMIDITY
    global HYST_HUMIDITY
    global COUNTER

    s = Logger()
    root_logger = s.getLogger()
    dht22 = humidity.DHT22()
    h, t = dht22.get_measurements()

    COUNTER += 1  

    if float(h) > MAX_HUMIDITY:    
        root_logger.info(': Fan running: Humidity: {} Temperature: {}'.format(h, t))
        WRITE_TOLOGG = True
        shortAirBlast(900)
        COUNTER = 0

    if float(h) < (MAX_HUMIDITY - HYST_HUMIDITY):
        fanOFF()  

        if COUNTER >= 440: # Periodic (1h) air blast to sens humidity
            shortAirBlast(180)
            COUNTER = 0
            root_logger.info(': Periodic fan run: Humidity: {} Temperature: {}'.format(h, t))

        if WRITE_TOLOGG:
            root_logger.info(': Fan stopped: Humidity: {} Temperature: {}'.format(h, t))
            WRITE_TOLOGG = False


def main():
    try:
        s = Logger()
        root_logger = s.getLogger()
        root_logger.info(': check_humidity started')
        setup()
        shortAirBlast(15)

        while True:
            time.sleep(5)
            check_humidity() #sleeps for 3.2 seconds


    except Exception as e:
        root_logger.error('MAIN: Error: ' + str(e))
        pass
    finally:
        GPIO.cleanup()
        sys.exit(0)


if __name__ == '__main__':
    main()
