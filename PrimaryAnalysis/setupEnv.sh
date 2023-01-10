#!/bin/bash

DFIDIR=`pwd`
echo $DFIDIR

# increase sub limits for slurm
echo "increasing SLURM array max size"
cp /usr/local/etc/slurm/slurm.conf fullNewSlurm.conf
chmod u+w fullNewSlurm.conf
cat confAdds.txt >> fullNewSlurm.conf
sudo mv fullNewSlurm.conf /usr/local/etc/slurm/slurm.conf

# install python locally in the DFI dir
echo "installing libffi-devel dependency"
sudo yum makecache
sudo yum -y install libffi-devel
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
python/3.7.8/bin/pip3.7 install protobuf==3.20.0
echo "installing numpy"
python/3.7.8/bin/pip3.7 install numpy==1.16.5
echo "installing scipy"
python/3.7.8/bin/pip3.7 install scipy==1.4.1
echo "installing tensorflow"
python/3.7.8/bin/pip3.7 install tensorflow==2.2.1
echo "installing keras"
python/3.7.8/bin/pip3.7 install keras==2.3.1
echo "installing opencv"
python/3.7.8/bin/pip3.7 install opencv-python==4.1.0.25
echo "installing google cloud storage"
python/3.7.8/bin/pip3.7 install google-cloud-storage
echo "installing keras_segmentation"
python/3.7.8/bin/pip3.7 install git+https://github.com/divamgupta/image-segmentation-keras.git@f04852d3d51ac278e9e527d2eed78eddc5d56872
echo "installing tqdm"
python/3.7.8/bin/pip3.7 install tqdm
echo "updating protobuf AFTER tensorflow installation"
python/3.7.8/bin/pip3.7 install protobuf==3.20.0

# set up the python module
echo "copying python to module location"
sudo cp -r python /apps/
sudo mkdir /apps/modulefiles/python
sudo mkdir /apps/modulefiles/python/3.7.8
sudo cp modulefile_for_python3.7.8.txt /apps/modulefiles/python/3.7.8

# load python and finish setting up the dir
echo "setting up SLURM log directory"
sudo mkdir slurmlogs
sudo chmod a+w slurmlogs/
# module load python/3.7.8

echo "Done."

