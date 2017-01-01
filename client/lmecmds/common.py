'''
Created on Dec 23, 2016

@author: devdatta
'''

import json
import logging
import os
import sys
import yaml

def read_app_info():
    cwd = os.getcwd()
    lmefile = cwd + "/lme.yaml"
    app_info = {}
    if not os.path.exists(lmefile):
        print("lme.yaml not present. Asking required app information from user.")
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
        dep_id = line['dep_id']
        version = line['version']
        cloud = line['cloud']
        artifact_info_dict = line['info']

        artifact_info = ''
        for key, value in artifact_info_dict.iteritems():
            artifact_info = artifact_info + key + ": " + value + "\n"
        row = [dep_id, version, cloud, artifact_info]
        pretty_table.add_row(row)

    return pretty_table