#!/bin/bash
# sets r/w permission for user 'pi' to all subdirectories in camera_scripts
# needs to be located within the same directory as camera_scripts
# use: bash submod.sh

for d in $(find /home/pi/camera_scripts -maxdepth 1 -type d)
do
  # set permission to files
  # directories are accessible with $d:
  sudo chown -R pi:pi $d
  sudo chmod -R 777 $d
  echo $d
done >output_file