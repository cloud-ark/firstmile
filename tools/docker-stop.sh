docker ps -a | grep -v firstmile | awk '{print $1}' | xargs docker stop
