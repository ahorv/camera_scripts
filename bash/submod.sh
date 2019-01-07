#!/bin/bash
# sets permission to all subdirectories 

for d in $(find /home/pi/python_scripts -maxdepth 1 -type d)
do
  #Do something, the directory is accessible with $d:
  sudo chown -R pi:pi $d
  sudo chmod -R 777 $d
  echo $d
done >output_file