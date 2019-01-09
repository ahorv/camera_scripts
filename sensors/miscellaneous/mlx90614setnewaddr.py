#########################################################################
##  08.12.2017 Version 2 : mlx90614setnewaddr.py
#########################################################################
# Erases old address of MLX90614 temperature sensor and sets a new address.
#
# NEW:
# -----
# - 0x5A is the default address with PEC -> 0xE1
# - The PEC is CRC-8 and must be calculated for each new address !
# - For further information see: p19 SMBus-communication-MLX90614
# - Note: any MLX90164 will respond to 0x00
#
#########################################################################

import smbus
from time import sleep
import infrared


def changeAdr():
    try:
        bus = smbus.SMBus(1)
        print("Old Adr: 0x%02X" % bus.read_word_data(0x00, 0x2E))
        bus.pec = True
        data = [0x00, 0x00, 0x6F]
        bus.write_i2c_block_data(0x00, 0x2E, data)

        sleep(0.005)

        #data = [newadr, 0x00, 0xF4]
        #data = [0x5B, 0x00, 0xF4]        # alternate addr if two MLX are used 
        data = [0x5A, 0x00, 0xE1]         # default addr: [0x5A, 0x00, 0xE1] -> PEC = 0xE1
        bus.write_i2c_block_data(0x00, 0x2E, data)
        sleep(0.005)
        print("New adr: 0x%02X" % bus.read_word_data(0x00, 0x2E))
        bus.pec = False

    except IOError as e:
        print('Error change Adr: {}'.format(e))
        sleep(0.01)

    

def main():
    try:        
        changeAdr()

        print('Done')

    except Exception as e:
        print('MAIN: Error: ' + str(e))


if __name__ == '__main__':
    main()
