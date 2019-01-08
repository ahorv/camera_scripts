#!/usr/local/bin/python

#########################################################################
##  26.01.2018 Version 1 : sun.py
#########################################################################
# Calculates sunrise and sunset with the aid of python's ephem.
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
#
######################################################################

# a Python script for PyEphem
import ephem
import datetime

# set location
o=ephem.Observer()
o.lat='47.014958'  # 47° 00' 53.8416'' N
o.long='8.305203'  #  8° 18' 18.63'' E
o.elev = 446
o.pressure= 0
o.horizon = '-0:34'

s=ephem.Sun()
s.compute()

fmt2 = '%Y-%m-%d %H:%M:%S'
dat = datetime.datetime.now()
print('Date and Time: {}'.format(dat.strftime(fmt2)))

print('\n')
print('Next Sun Rise: {}'.format(ephem.localtime(o.next_rising(s)).strftime(fmt2)))
print('Next Sun Set : {}'.format(ephem.localtime(o.next_setting(s)).strftime(fmt2)))