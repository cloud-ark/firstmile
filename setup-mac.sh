#!/bin/bash

-- Test -- 

# Check if running as root -- if so, exit
if (( $EUID == 0 )); then
   echo "Looks like you are trying to run install.sh as root."
   echo "That is not required actually."
   echo "Just run ./install.sh as regular user."
   exit
fi

# Check if Docker is installed
docker_version=`ls -l /Applications | grep -i docker`
if [[ -z "$docker_version" ]]; then
   echo "Looks like Docker is not installed. Please install Docker as it is required for FirstMile."
   echo "Refer: https://docs.docker.com/docker-for-mac/"
   exit
fi

# define installation log file
rm -rf install.log
touch install.log
install_log="install.log"
echo "Installing FirstMile. Installation logs stored in $install_log"

# Determine Docker HOST IP
DOCKER_MACHINE_ENV=`docker-machine env default` || { echo "docker-machine env default failed" ; exit 1; }
cat > docker_machine_env <<EOF
  echo $DOCKER_MACHINE_ENV
EOF
DOCKER_HOST=`grep DOCKER_HOST docker_machine_env | sed 's/\// /'g | sed 's/:/ /'g | awk '{print $3}'`
echo "DOCKER_HOST=$DOCKER_HOST"
echo "DOCKER_HOST=$DOCKER_HOST" > ./client/cldcmds/docker_host.txt

# Install FirstMile client
echo "Installing FirstMile client"
pip install virtualenv >> $install_log
virtenv="firstmile"
virtualenv --python=python2.7 $virtenv >> $install_log
source $virtenv/bin/activate >> $install_log
cd client
../$virtenv/bin/python setup.py install >> $install_log
export PATH=$PATH:`pwd`
export PYTHONPATH=$PYTHONPATH:`pwd`
cd ..

# Update .bashrc and .profile so that cld client will be in PATH/PYTHONPATH
$virtenv/bin/pip install -r requirements.txt >> $install_log
pushd $virtenv/bin
export PATH=$PATH:`pwd`
echo '### Added by FirstMile' >> ~/.profile
echo "export PATH=`pwd`:$PATH" >> ~/.profile
echo '### Added by FirstMile' >> ~/.bashrc
echo "export PATH=`pwd`:$PATH" >> ~/.bashrc
export PYTHONPATH=$PYTHONPATH:`pwd`
echo "export PYTHONPATH=`pwd`:$PYTHONPATH" >> ~/.profile
echo "export PYTHONPATH=`pwd`:$PYTHONPATH" >> ~/.bashrc
popd

# Generate Dockerfile
rm -rf Dockerfile
touch Dockerfile
echo "FROM ubuntu:14.04" >> Dockerfile
echo "RUN apt-get update && apt-get install -y docker.io python-dev python-setuptools python-pip git sudo curl mysql-client-core-5.5 \\" >> Dockerfile
echo "    && pip install urllib3==1.14" >> Dockerfile
echo "RUN sudo useradd -ms /bin/bash -d /home/ubuntu ubuntu && echo \"ubuntu:ubuntu\" | chpasswd && adduser ubuntu sudo \\" >> Dockerfile
echo "    && echo \"ubuntu ALL=(ALL) NOPASSWD: ALL\" >> /etc/sudoers \\" >> Dockerfile
echo "    && sudo usermod -aG root ubuntu && sudo usermod -aG staff ubuntu && sudo adduser ubuntu docker " >> Dockerfile
echo "ADD . /src" >> Dockerfile
echo "WORKDIR /src" >> Dockerfile
echo "RUN chown ubuntu:ubuntu -R ." >> Dockerfile
echo "USER ubuntu" >> Dockerfile
echo "RUN sudo pip install -r requirements.txt" >> Dockerfile
echo "EXPOSE 5002" >> Dockerfile
HOST_HOME="$HOME/.cld/data/deployments"
echo "ENV HOST_HOME $HOST_HOME" >> Dockerfile
echo "CMD [\"python\", \"/src/cld.py\"]" >> Dockerfile

# Start the firstmile server container
#set -x
#echo "Starting FirstMile"
#eval "$(docker-machine env default)"
#docker build -t firstmile-img . >> $install_log
#docker run -u ubuntu -p 5002:5002 -v /var/run/docker.sock:/var/run/docker.sock -v $HOME:/home/ubuntu -d firstmile-img >> $install_log

#has_server_started=`docker ps -a | grep firstmile`

#if [[ ! -z "${has_server_started}" ]]; then
#    echo "FirstMile successfully installed."
#    echo "Next steps:"
#    echo "- Quick test: Run 'cld app list'"
#    echo "- Try sample programs from examples directory"
#fi

# Activate the virtual environment in which we have installed the FirstMile client.
#/bin/bash -c ". $virtenv/bin/activate; exec /bin/bash -i"

