docker ps -a | awk '{print $1}' | xargs docker stop
