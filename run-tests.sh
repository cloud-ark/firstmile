#!/bin/bash

echo "Running functional tests for local-docker"
#cd tools
#./docker-cleanup.sh
#cd ..
python -m testtools.run functionaltests.local.test_local.TestLocal.test_app_deploy_no_service
python -m testtools.run functionaltests.local.test_local.TestLocal.test_app_deploy_with_mysql_service
python -m testtools.run functionaltests.local.test_local.TestLocal.test_mysql_instance_provision

echo "Running functional tests for google"
#cd tools
#./docker-cleanup.sh
#cd ..
python -m testtools.run functionaltests.google.test_google.TestGoogle.test_app_deploy_no_service
python -m testtools.run functionaltests.google.test_google.TestGoogle.test_app_deploy_with_mysql_service
python -m testtools.run functionaltests.google.test_google.TestGoogle.test_mysql_instance_provision

echo "Running functional tests for aws"
#cd tools
#./docker-cleanup.sh
#cd ..
python -m testtools.run functionaltests.aws.test_aws.TestAWS.test_app_deploy_no_service

