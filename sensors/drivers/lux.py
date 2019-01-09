#!/usr/bin/env python
'''
TSL2561 driver.
'''

import smbus
from time import  sleep
 
class TSL2561():
    
    def __init__(self, address = 0x39, bus_num=1):

        self.bus = smbus.SMBus(bus=bus_num)   
        self.bus.write_byte_data(0x39, 0x00 | 0x80, 0x03)
        self.bus.write_byte_data(0x39, 0x01 | 0x80, 0x02) 
        sleep(0.5)
 
    def read_reg_A(self):
        data = self.bus.read_i2c_block_data(0x39, 0x0C | 0x80, 2)
        return data

    def read_reg_B(self):        
        data1 = self.bus.read_i2c_block_data(0x39, 0x0E | 0x80, 2)
        return data1

    def get_full_spectrum(self):
        data = self.read_reg_A()
        ch0 = data[1] * 256 + data[0]
        return ch0

    def get_infrared(self):
        data1 = self.read_reg_B()
        ch1 = data1[1] * 256 + data1[0]
        return ch1

    def get_visible_spectrum(self):
        ch0 = self.get_full_spectrum()
        ch1 = self.get_infrared()
        delta = (ch0 - ch1)
        return delta

    def get_full_infra_visi(self):
        full = self.get_full_spectrum()
        infr = self.get_infrared()
        visi = self.get_visible_spectrum()
        self.bus.close()
        return full,infr,visi
    

'''
if __name__ == "__main__":
    sensor = TSL2561()
    print( "Full Spectrum(IR + Visible) :{0:.4f}lux".format(sensor.get_full_spectrum()))
    print( "Infrared Value :{0:.4f}lux".format(sensor.get_infrared()))
    print( "Visible Value  :{0:.4f}lux".format(sensor.get_visible_spectrum()))
'''

