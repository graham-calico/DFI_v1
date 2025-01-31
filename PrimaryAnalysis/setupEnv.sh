#!/bin/bash

DFIDIR=`pwd`
echo $DFIDIR

# install python locally in the DFI dir
echo "installing libffi-devel dependency"
sudo apt update
sudo apt-get install libffi-dev
echo "installing python v3.7.8"
mkdir python
mkdir python/3.7.8
LOCPYPATH=${DFIDIR}"/python/3.7.8"
echo $LOCPYPATH
sudo curl -O https://www.python.org/ftp/python/3.7.8/Python-3.7.8.tgz
sudo tar -xzf Python-3.7.8.tgz
cd Python-3.7.8
sudo ./configure --enable-optimizations --prefix=$LOCPYPATH --exec-prefix=$LOCPYPATH
sudo make altinstall
cd ..

# locally install all of the modules
echo "updating protobuf"
python/3.7.8/bin/pip3.7 install protobuf==3.20.0 --no-warn-script-location 
echo "installing numpy"
python/3.7.8/bin/pip3.7 install numpy==1.16.5 --no-warn-script-location 
echo "installing scipy"
python/3.7.8/bin/pip3.7 install scipy==1.4.1 --no-warn-script-location 
echo "installing tensorflow"
python/3.7.8/bin/pip3.7 install tensorflow==2.2.1 --no-warn-script-location 
echo "installing keras"
python/3.7.8/bin/pip3.7 install keras==2.3.1 --no-warn-script-location 
echo "installing opencv"
python/3.7.8/bin/pip3.7 install opencv-python==4.1.0.25 --no-warn-script-location 
echo "installing google cloud storage"
python/3.7.8/bin/pip3.7 install google-cloud-storage --no-warn-script-location 
echo "downgrade urllib3 version used by google-cloud-storage"
python/3.7.8/bin/pip3.7 install urllib3==1.26.16 --no-warn-script-location 
echo "installing keras_segmentation"
python/3.7.8/bin/pip3.7 install git+https://github.com/divamgupta/image-segmentation-keras.git@f04852d3d51ac278e9e527d2eed78eddc5d56872 --no-warn-script-location 
echo "installing tqdm"
python/3.7.8/bin/pip3.7 install tqdm --no-warn-script-location 
echo "updating protobuf AFTER tensorflow installation"
python/3.7.8/bin/pip3.7 install protobuf==3.20.0 --no-warn-script-location 

# set up the python module
echo "copying python to module location"
sudo cp -r python /opt/apps/
sudo mkdir /opt/apps/modulefiles/python
sudo mkdir /opt/apps/modulefiles/python/3.7.8
sudo cp modulefile_for_python3.7.8.txt /opt/apps/modulefiles/python/3.7.8

# load python and finish setting up the dir
echo "setting up SLURM log directory"
sudo mkdir slurmlogs
sudo chmod a+w slurmlogs/
# module load python/3.7.8

echo "Done."

