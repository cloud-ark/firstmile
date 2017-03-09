#!/bin/bash

release_file=RELEASES
version=0.1
TARGET="/home/devdatta/Code/firstmile-distributions/firstmile-$version"

if [[ ! -e $TARGET ]]; then 
   mkdir -p $TARGET
fi

# Checkout right repository
pushd $TARGET
git clone https://devdattakulkarni@bitbucket.org/devdattakulkarni/lme.git firstmile
cd firstmile
git checkout remotes/origin/service-app-separation

sha=`git log --oneline | head -1`

today=`date`
echo "$today $version $sha" >> ../../$release_file

python -m compileall .

# Remove .py files
find . | grep py | grep -v pyc | grep -v "lib.linux" | grep -v dist | xargs rm

# Remove .git folder
rm -rf .git

# Remove unwanted files
rm -rf Dockerfiles
rm -rf build
rm -rf dist
rm cld.egg-info
rm -rf packaging
rm deployment-details.txt
rm client/lmecli.pyc
rm client/lmeui.pyc
rm client/small-devcentric.png


# Clone lme-examples
cd ..
git clone https://devdattakulkarni@bitbucket.org/devdattakulkarni/lme-examples.git firstmile-samples

# Remove .git
cd firstmile-samples
rm -rf .git

cd ../..
echo "Creating tar file for release"
tar -cvf firstmile-$version.tar firstmile-$version

echo "Gzipping release"
gzip firstmile-$version.tar

echo "Release is ready"

# 2. Create a virtual environment
#cd ..
#virtualenv firstmile-env
#./firstmile-env/bin/python lme/client/setup.py install

# 3. Compile the source code 
#./firstmile-env/bin/python -m compileall .

# 4. Install the cld client
#cd firstmile/client
#../../firstmile-env/bin/python setup.py install

# 5. Install server's requirements.txt
#cd ..
#../firstmile-env/bin/pip install -r requirements.txt

# 6. Start the server
#nohup python cld.pyc 1>>cld-server.log 2>&1 &
