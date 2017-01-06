'''
Created on Dec 23, 2016

@author: devdatta
'''

import json
import logging
import os
import sys
import yaml

from os.path import expanduser

home_dir = expanduser("~")

APP_STORE_PATH = ("{home_dir}/.lme/data/deployments").format(home_dir=home_dir)

def setup_aws(dest):
    aws_creds_path = APP_STORE_PATH + "/aws-creds"
    if not os.path.exists(aws_creds_path):
        os.makedirs(aws_creds_path)
        access_key_id = raw_input("Enter AWS Access Key:")
        secret_access_key = raw_input("Enter AWS Secret Access Key:")
        fp = open(aws_creds_path + "/credentials", "w")
        fp.write("[default]\n")
        fp.write("aws_access_key_id = %s\n" % access_key_id)
        fp.write("aws_secret_access_key = %s\n" % secret_access_key)
        fp.close()

        fp = open(aws_creds_path + "/config", "w")
        fp.write("[default]\n")
        fp.write("output = json\n")
        fp.write("region = us-west-2\n")
        fp.close()

def read_app_info():
    cwd = os.getcwd()
    lmefile = cwd + "/lme.yaml"
    app_info = {}
    if not os.path.exists(lmefile):
        return app_info

    fp = open(lmefile, "r")
    lme_obj = yaml.load(fp.read())
    application_obj = lme_obj['application']
    app_type = application_obj['type']
    entry_point = application_obj['entry_point']

    app_info['app_type'] = app_type
    app_info['entry_point'] = entry_point

    app_name = cwd[cwd.rfind("/")+1:]

    app_info['app_name'] = app_name

    if 'env_variables' in application_obj:
        env_var_obj = application_obj['env_variables']
        app_info['env_variables'] = env_var_obj

    if 'app_variables' in application_obj:
        app_var_obj = application_obj['app_variables']
        app_info['app_variables'] = app_var_obj

    return app_info

def read_service_info():
    cwd = os.getcwd()
    lmefile = cwd + "/lme.yaml"
    service_info = {}
    if not os.path.exists(lmefile):
        print("lme.yaml not present. Asking required service information from user.")
        return service_info

    fp = open(lmefile, "r")
    lme_obj = yaml.load(fp.read())
    if 'services' in lme_obj:
        service_info = lme_obj['services']

    return service_info

def read_cloud_info():
    cwd = os.getcwd()
    lmefile = cwd + "/lme.yaml"
    cloud_info = {}
    if not os.path.exists(lmefile):
        return cloud_info

    fp = open(lmefile, "r")
    lme_obj = yaml.load(fp.read())
    cloud_obj = lme_obj['cloud']

    cloud_info['type'] = cloud_obj['type']
    if cloud_obj['type'] == 'local':
        app_port = '5000'
        if cloud_obj['app_port']:
            app_port = cloud_obj['app_port']
            cloud_info['app_port'] = app_port
    if cloud_obj['type'] == 'google':
        if not cloud_obj['project_id']:
            print("project_id required for cloud %s" % cloud_obj['type'])
            sys.exit(0)
        else:
            project_id = cloud_obj['project_id']
            cloud_info['project_id'] = project_id
        if not cloud_obj['user_email']:
            print("user_email required for cloud %s" % cloud_obj['type'])
            sys.exit(0)
        else:
            user_email = cloud_obj['user_email']
            cloud_info['user_email'] = user_email

    return cloud_info

def artifact_name_show(result, pretty_table):
    status_json = json.loads(result)
    app_status_list = status_json['data']

    logging.debug(app_status_list)

    for line in app_status_list:
        name = line['name'] if 'name' in line else ''
        dep_id = line['dep_id'] if 'dep_id' in line else ''
        version = line['version'] if 'version' in line else ''
        cloud = line['cloud'] if 'cloud' in line else ''
        status = line['status'] if 'status' in line else ''
        artifact_info_dict = line['info'] if 'info' in line else {}

        artifact_info = ''
        if artifact_info_dict:
            for key, value in artifact_info_dict.iteritems():
                artifact_info = artifact_info + key + ": " + value + "\n"
        row = [dep_id, name, version, cloud, status, artifact_info]
        pretty_table.add_row(row)

    return pretty_table