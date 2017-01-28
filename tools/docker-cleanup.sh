#!/bin/bash

echo "Stopping all running Docker containers"
./docker-stop.sh

echo "Removing all running Docker containers"
./docker-rm.sh

echo "Removing all Docker container images"
./docker-rmi.sh
