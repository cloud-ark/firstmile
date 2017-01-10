'''
Created on Dec 23, 2016

@author: devdatta
'''

import json
import logging
import os
import subprocess
import sys
import yaml

from os.path import expanduser

home_dir = expanduser("~")

APP_STORE_PATH = ("{home_dir}/.lme/data/deployments").format(home_dir=home_dir)

LOCAL_DOCKER = "local-docker"
GOOGLE = "google"
AWS = "aws"

def get_google_project_user_details(project_location):
    google_app_details_path = APP_STORE_PATH + "/google-creds/app_details.txt"
    app_name = project_location[project_location.rfind("/")+1:]
    project_id = ''
    user_email = ''
    if os.path.exists(google_app_details_path):
        fp = open(google_app_details_path, "r")
        lines = fp.readlines()
        for line in lines:
            parts = line.split(":")
            potential_project_id = parts[1].rstrip().lstrip()
            if line.find("User Email") >=0:
                user_email = parts[1].rstrip().lstrip()
            if potential_project_id.find(app_name) >= 0:
                project_id = potential_project_id
        if not user_email:
            user_email = raw_input("Enter Gmail address associated with your Google App Engine account>")
            fp = open(google_app_details_path, "a")
            fp.write("User Email:%s\n" % user_email)
            fp.close()
        if not project_id:
            project_id = raw_input("Enter project id>")
            fp = open(google_app_details_path, "a")
            fp.write("Project ID:%s\n" % project_id)
            fp.close()
    else:
        project_id = raw_input("Enter project id>")
        user_email = raw_input("Enter Gmail address associated with your Google App Engine account>")
        fp = open(google_app_details_path, "w")
        fp.write("User Email:%s\n" % user_email)
        fp.write("Project ID:%s\n" % project_id)
        fp.close()
    return project_id, user_email

def setup_google(dest):
    google_creds_path = APP_STORE_PATH + "/google-creds"
    if not os.path.exists(google_creds_path):
        os.makedirs(google_creds_path)

        df = ("FROM ubuntu:14.04 \n"
              "RUN apt-get update && apt-get install -y wget python \n"
              "RUN sudo wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-126.0.0-linux-x86_64.tar.gz && \ \n"
              "    sudo gunzip google-cloud-sdk-126.0.0-linux-x86_64.tar.gz && \ \n"
              "    sudo tar -xvf google-cloud-sdk-126.0.0-linux-x86_64.tar \n"
              "RUN /google-cloud-sdk/bin/gcloud components install beta \n"
              "ENTRYPOINT [\"/google-cloud-sdk/bin/gcloud\", \"beta\", \"auth\", \"login\", \"--no-launch-browser\"] \n")

        docker_file = open(google_creds_path + "/Dockerfile", "w")
        docker_file.write(df)
        docker_file.close()

        app_name = cwd = os.getcwd()
        os.chdir(google_creds_path)
        k = app_name.rfind("/")
        app_name = app_name[k+1:]

        docker_build_cmd = ("docker build -t {app_name}_creds .").format(app_name=app_name)
        os.system(docker_build_cmd)

        docker_run_cmd = ("docker run -i -t {app_name}_creds").format(app_name=app_name)
        os.system(docker_run_cmd)

        cont_id_cmd = ("docker ps -a | grep {app_name}_creds | cut -d ' ' -f 1 | head -1").format(app_name=app_name)
        cont_id = subprocess.check_output(cont_id_cmd, shell=True).rstrip().lstrip()

        copy_file_cmd = ("docker cp {cont_id}:/root/.config/gcloud {google_creds_path}").format(cont_id=cont_id,
                                                                                                 google_creds_path=google_creds_path)
        os.system(copy_file_cmd)

        os.chdir(cwd)

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
        # print("lme.yaml not present. Asking required service information from user.")
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
    if cloud_obj['type'] == LOCAL_DOCKER:
        app_port = '5000'
        if cloud_obj['app_port']:
            app_port = cloud_obj['app_port']
            cloud_info['app_port'] = app_port
    if cloud_obj['type'] == GOOGLE:
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