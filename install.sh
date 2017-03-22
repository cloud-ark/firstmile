#!/bin/bash

# define installation log file
truncate -s 0 install.log
install_log="install.log"
echo "Installing FirstMile. Installation logs stored in $install_log"

# Check if the platform is one that we support
declare -a supported_platform_list=("Ubuntu 14.04", "OS X");
platform=`uname -a | grep 14.04`

if [[ ! -z "$platform" ]]; then
   echo "Unsupported platform. Currently supported platform: $supported_platform_list"
fi

# Install requirements
sudo apt-get update &>> $install_log && sudo apt-get install -y docker.io python-dev python-pip &>> $install_log

sudo usermod -aG docker $USER &>> $install_log
# Adding the current user to docker group so docker commands can be run without sudo
sudo gpasswd -a ${USER} docker &>> $install_log
sudo service docker restart &>> $install_log


# Install FirstMile client
echo "Installing FirstMile client"
#echo "Creating virtual environment"
sudo pip install virtualenv &>> $install_log
virtenv="firstmile"
sudo virtualenv $virtenv &>> $install_log
source $virtenv/bin/activate &>> $install_log

#if [[ ! -e cld.pyc ]]; then
#sudo ./$virtenv/bin/python -m compileall . &>> $install_log
#fi

cd client
sudo ../$virtenv/bin/python setup.pyc install &>> $install_log
export PATH=$PATH:`pwd`
export PYTHONPATH=$PYTHONPATH:`pwd`
cd ..

# ?
sudo $virtenv/bin/pip install -r requirements.txt &>> $install_log

pushd $virtenv/bin
export PATH=$PATH:`pwd`
export PYTHONPATH=$PYTHONPATH:`pwd`
popd

#echo "Starting firstmile server. Server logs stored in cld-server.log"
#echo "Home:$HOME"
#sudo groupadd docker


# Starting a sub-shell to enable the docker group that we set above
#echo "Executing newgrp command"
#/usr/bin/newgrp docker <<EONG
#EONG
#echo "Done executing newgrp command"

# Find id of docker group
docker_group_id=`getent group docker | cut -d: -f3`

# Generate Dockerfile
truncate -s 0 Dockerfile
echo "FROM ubuntu:14.04" >> Dockerfile
echo "RUN apt-get update && apt-get install -y docker.io python-dev python-setuptools python-pip git sudo curl \\" >> Dockerfile
echo "    && pip install urllib3==1.14" >> Dockerfile
echo "RUN sudo useradd -ms /bin/bash -d /home/ubuntu ubuntu && echo \"ubuntu:ubuntu\" | chpasswd && adduser ubuntu sudo \\" >> Dockerfile
echo "    && echo \"ubuntu ALL=(ALL) NOPASSWD: ALL\" >> /etc/sudoers \\" >> Dockerfile
echo "    && sudo usermod -aG root ubuntu && sudo groupmod --gid $docker_group_id docker && sudo usermod --groups $docker_group_id ubuntu" >> Dockerfile
echo "ADD . /src" >> Dockerfile
echo "WORKDIR /src" >> Dockerfile
echo "RUN chown ubuntu:ubuntu -R ." >> Dockerfile
echo "USER ubuntu" >> Dockerfile
echo "RUN sudo pip install -r requirements.txt" >> Dockerfile
echo "EXPOSE 5002" >> Dockerfile
echo "CMD [\"python\", \"/src/cld.pyc\"]" >> Dockerfile

# Start the firstmile server container
#set -x
echo "Starting FirstMile"
sg docker -c "docker build -t firstmile-img . &>> $install_log"
sg docker -c "docker run -u ubuntu -p 5002:5002 -v /var/run/docker.sock:/var/run/docker.sock -v $HOME:/home/ubuntu -d firstmile-img &>> $install_log"

has_server_started=`sg docker -c "docker ps -a | grep firstmile"`

if [[ ! -z "${has_server_started}" ]]; then
    echo "FirstMile successfully installed."
    echo "Next steps:"
    echo "- Quick try: Run 'cld app list'"
    echo "- Then try out samples from firstmile-samples directory (available one level above)"
    echo "Happy coding :-)"
fi

# Activate the virtual environment in which we have installed the FirstMile client.
/bin/bash -c ". $virtenv/bin/activate; exec /bin/bash -i"

#docker run -u $USER:$USER -p 5002:5002 -v /var/run/docker.sock:/var/run/docker.sock -v $HOME:/$USER -d firstmile-img
#sudo source $virtenv/bin/activate
#alias activate=". $virtenv/bin/activate"

#sudo activate

#ps -eaf | grep 'python cld.py' | awk '{print $2}' | xargs kill
#pip install -r requirements.txt
#nohup python cld.pyc 1>>cld-server.log 2>&1 &

#exec -c "source $virtenv/bin/activate"
