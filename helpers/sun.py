#!/usr/bin/env python

#########################################################################
##  26.01.2018 Version 1 : sun.py
#########################################################################
# Calculates sunrise and sunset with the aid of python's ephem.
# Sets according to calculated sunrise and sunset new start and stop
# times for the picamera - cronjob in the crontab.
#
# NEW:
# -----
# - 26.01.2018: first implemented
#
#########################################################################
# Remarks:
#------------------------------------------------------------------------
# Helpful online tutorials and tools:
#
# https://www.sonnenverlauf.de/#/47.0502,8.3093,13/2018.06.05/11:23/1/0
# https://www.esrl.noaa.gov/gmd/grad/solcalc/sunrise.html
# https://www.latlong.net/lat-long-dms.html
# https://chrisramsay.co.uk/posts/2017/03/fun-with-the-sun-and-pyephem/ (sun's position)
# https://code.tutsplus.com/tutorials/managing-cron-jobs-using-python--cms-28231
######################################################################

# a Python script for PyEphem
import ephem
import datetime
from datetime import datetime
from crontab import CronTab

def calc_sun():
    # set location
    o=ephem.Observer()
    o.lat='47.014958'  # 47° 00' 53.8416'' N
    o.long='8.305203'  #  8° 18' 18.63'' E
    o.elev = 446
    o.pressure= 0
    o.horizon = '-0:34'

    s=ephem.Sun()
    s.compute()

    fmt1 = '%Y-%m-%d %H:%M:%S'
    fmt2 = '%H:%M:%S'
    dat = datetime.now()
    print('Date and Time: {}'.format(dat.strftime(fmt2)))

    print('\n')
    sunrise = '{}'.format(ephem.localtime(o.next_rising(s)).strftime(fmt2))
    sunset  = '{}'.format(ephem.localtime(o.next_setting(s)).strftime(fmt2))

    print('Next Sun Rise: {}'.format(sunrise))
    print('Next Sun Set : {}'.format(sunset))

    return sunrise,sunset

def create_cronjob(start, stop) :
    job_path      =  '/home/pi/.virtualenvs/cv/bin/python3 /home/pi/python_scripts/picam/picam.py'
    my_cron = CronTab(user='pi')
    job = my_cron.new(command=job_path, comment='picamera')

    from_to = str(start) + '-' + str(stop)
    job.setall('*/10',from_to, '*','*','*')
    my_cron.write()

def update_cronjob(start, stop):
    # set new start and stop times for picamera cronjob
    job_path      =  '/home/pi/.virtualenvs/cv/bin/python3 /home/pi/python_scripts/picam/picam.py'
    my_cron = CronTab(user='pi')

    job = my_cron.new(command=job_path, comment='picamera')

    for job in my_cron:
        if job.comment == 'picamera':
            my_cron.remove(job)
            my_cron.write()

    create_cronjob(start, stop)
    job.enable()

def rounder(str_time):

    t = datetime.strptime(str_time, '%H:%M:%S').time()
    if t.minute >= 30:
        return t.replace(second=0, microsecond=0, minute=0, hour=t.hour+1)
    else:
        return t.replace(second=0, microsecond=0, minute=0)

def main():
    try:
        sunrise, sunset = calc_sun()
        update_cronjob(rounder(sunrise), rounder(sunset))

    except Exception as e:
        print('Error in MAIN: ' + str(e))


if __name__ == '__main__':
    main()
