#!/bin/bash

echo "Creating test virtual environment"
pip install virtualenv
virtenv=test-cld
virtualenv $virtenv
source $virtenv/bin/activate

echo "Installing client"
cd client
sudo python setup.py install
cd ..

echo "Starting server. Server logs stored in cld-server.log"
ps -eaf | grep 'python cld.py' | awk '{print $2}' | xargs kill
pip install -r requirements.txt
nohup python cld.py 1>>cld-server.log 2>&1 &
