docker images | grep -v firstmile | awk '{print $3'} | xargs docker rmi -f
