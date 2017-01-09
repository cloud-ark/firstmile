'''
Created on Jan 3, 2017

@author: devdatta
'''
from os.path import expanduser

DEFAULT_DB_USER = 'testuser'
DEFAULT_DB_PASSWORD = 'testpass123!#$'
DEFAULT_DB_NAME = 'testdb'

home_dir = expanduser("~")

APP_STORE_PATH = ("{home_dir}/.lme/data/deployments").format(home_dir=home_dir)

GOOGLE_CREDS_PATH = APP_STORE_PATH + "/google-creds"

DEPLOYING_APP = "DEPLOYING_APP"
APP_DEPLOYMENT_COMPLETE = "APP_DEPLOYMENT_COMPLETE"

DEPLOYING_SERVICE_INSTANCE = "DEPLOYING_SERVICE_INSTANCE"
SERVICE_INSTANCE_DEPLOYMENT_COMPLETE = "SERVICE_DEPLOYMENT_COMPLETE"