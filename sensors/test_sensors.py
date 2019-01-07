#!/usr/bin/env python

import os
import sys
import logging
import logging.handlers
from time import sleep
from datetime import datetime
from os.path import basename

import lux
import infrared
import temperature
import rgb
import humidity

######################################################################
## Hoa: 24.12.2017 Version 2 : test_sensors.py
######################################################################
# This script calls each sensor for testing purposes. 
#
# New /Changes:
# ----------------------------------------------------------------------
#
# 10.12.2017 : Implemented
# 24.12.2017 : Added second temperatur sensor for camera 3 (test_Temp_Ambi)
#              This temperature sensor is not available in camera 1 & 2 !
# 24.12.2017 : Added humidity sensor.
#
######################################################################


def test_Temp_Dom():
    try:
        DS18B = temperature.DS18B20()
        DS18B_Dome_Temp = DS18B.get_cameradome_temp()

        print('DS18 Dom  Temp-sensor: Temp : {} '.format(DS18B_Dome_Temp))
    except Exception as e:
        print('DS18 Temp sensor error: ' + str(e))
        
def test_Temp_Ambi():
    try:
        DS18B = temperature.DS18B20()
        DS18B_Ambi_Temp = DS18B.get_ambient_temp()

        print('DS18 Ambi Temp-sensor: Temp : {} '.format(DS18B_Ambi_Temp))
    except Exception as e:
        print('DS18 Temp sensor error: ' + str(e))

def test_humi_temp():
    try:
        DHT22 = humidity.DHT22()
        humi,temp = DHT22.get_measurements()

        print('Humidity-sensor:  Humidity: {} Temp : {} '.format(humi,temp))
    except Exception as e:
        print('Humidity sensor error: ' + str(e))
    
def test_LUX():
    try:
        TSL = lux.TSL2561()
        Full, Infra, Visib = TSL.get_full_infra_visi()
        print('Lux-sensor:  Full_Spec: {} Infra_Spec: {} Visible_Spec: {}'.format(Full, Infra, Visib))
    except Exception as e:
        print('LUX sensor error: ' + str(e))

def test_MLX():
    try:
        MLX = infrared.MLX90614()
        print("Ambient temperature: {0:.4f}".format(MLX.get_amb_temp()))
        print("Object temperature:  {0:.4f}".format(MLX.get_obj_temp()))
    except Exception as e:
        print('MLX error: ' + str(e))

def test_RGB():
    try:
        TCS = rgb.TCS34725()
        TCS_R, TCS_G, TCS_B = TCS.get_RGB()
        print('RGB-sensor:  R: {} B: {} G: {}'.format(TCS_R, TCS_B, TCS_G))
    except Exception as e:
        print('RGB-sensor error: ' + str(e))

def main():
    try:

        print('Start test Sensors')
        cnt = 1

        while cnt < 21:

            print("Run: {0}".format(cnt))
            sleep(5)
            test_Temp_Dom()
            #sleep(5)          # uncomment for camera 3
            #test_Temp_Ambi()  # uncomment for camera 3
            sleep(1)
            test_humi_temp()
            sleep(1)
            test_LUX()
            sleep(1)
            test_MLX()
            sleep(1)
            test_RGB()
            print('\n')
            cnt += 1



        print('done')

    except Exception as e:
        print('MAIN: Error: ' + str(e))


if __name__ == '__main__':
    main()
