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
import shutil

from os.path import expanduser

home_dir = expanduser("~")

APP_STORE_PATH = ("{home_dir}/.cld/data/deployments").format(home_dir=home_dir)

LOCAL_DOCKER = "local-docker"
GOOGLE = "google"
AWS = "aws"
MYSQL = "mysql"
DEFAULT_APP_PORT = "5000"
DEFAULT_APP_TYPE = "python"

def verify_inputs(service, dest):
    improper_inputs = False
    if service and service.lower() != MYSQL:
        improper_inputs = True
        print("Incorrect service specified %s." % service)
        print("Supported options: %s" % MYSQL)

    dest = dest.lower() if dest else ''
    if dest and dest != GOOGLE and dest != AWS and dest != LOCAL_DOCKER:
        improper_inputs = True
        print("Incorrect destination cloud specified %s." % (dest))
        print("Supported options: %s, %s, %s" % (LOCAL_DOCKER, AWS, GOOGLE))

    if improper_inputs:
        exit()

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

def parse_artifact_name_and_version(line_contents):
    artifact = line_contents[1].rstrip().lstrip()
    k = artifact.rfind("--")
    artifact_version = artifact[k+2:].rstrip().lstrip()
    artifact_name = artifact[:k]
    return artifact_name, artifact_version

def reset_google():
    print("Removing google-creds directory from %s" % APP_STORE_PATH)
    google_creds_path = APP_STORE_PATH + "/google-creds"
    if os.path.exists(google_creds_path):
        shutil.rmtree(google_creds_path)

    print("Removing app-created.txt from various apps in %s" % APP_STORE_PATH)
    fp = open(APP_STORE_PATH + "/app_ids.txt")
    all_lines = fp.readlines()
    for line in all_lines:
        line_contents = line.split(" ")
        app_name, app_version = parse_artifact_name_and_version(line_contents)
        app_created_file = APP_STORE_PATH + "/" + app_name + "/app-created.txt"
        if os.path.exists(app_created_file):
            os.remove(app_created_file)

def setup_google(dest):
    google_creds_path = APP_STORE_PATH + "/google-creds"
    if not os.path.exists(google_creds_path):
        os.makedirs(google_creds_path)

        df = ("FROM lmecld/clis:gcloud \n"
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

        # Remove container created to obtain creds
        cont_name = ("{app_name}_creds").format(app_name=app_name)
        stop_cmd = ("docker ps -a | grep {cont_name} | cut -d ' ' -f 1 | xargs docker stop").format(cont_name=cont_name)
        os.system(stop_cmd)

        rm_cmd = ("docker ps -a | grep {cont_name} | cut -d ' ' -f 1 | xargs docker rm").format(cont_name=cont_name)
        os.system(rm_cmd)

        rmi_cmd = ("docker images -a | grep {cont_name}  | awk \'{{print $3}}\' | xargs docker rmi -f").format(cont_name=cont_name)
        os.system(rmi_cmd)

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
    lmefile = cwd + "/cld.yaml"
    app_info = {}
    if not os.path.exists(lmefile):
        return app_info

    fp = open(lmefile, "r")
    lme_obj = yaml.load(fp.read())

    for ob in lme_obj:
        if 'application' in ob:
            application_obj = ob['application']
            break

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

    app_port = DEFAULT_APP_PORT
    if application_obj['app_port']:
        app_port = application_obj['app_port']
    app_info['app_port'] = app_port

    return app_info

def read_service_info():
    cwd = os.getcwd()
    lmefile = cwd + "/cld.yaml"
    service_info = {}
    if not os.path.exists(lmefile):
        return service_info

    fp = open(lmefile, "r")
    lme_obj = yaml.load(fp.read())

    for ob in lme_obj:
        if 'services' in ob:
            service_info = ob['services']
            break
    return service_info

def read_cloud_info():
    cwd = os.getcwd()
    lmefile = cwd + "/cld.yaml"
    cloud_info = {}
    if not os.path.exists(lmefile):
        return cloud_info

    fp = open(lmefile, "r")
    lme_obj = yaml.load(fp.read())

    for ob in lme_obj:
        if 'cloud' in ob:
            cloud_obj = ob['cloud']
            break

    cloud_info['type'] = cloud_obj['type']
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

def artifact_list_show(result, pretty_table):
    status_json = json.loads(result)
    app_status_list = status_json['data']

    logging.debug(app_status_list)

    for line in app_status_list:
        name = line['name'] if 'name' in line else ''
        dep_id = line['dep_id'] if 'dep_id' in line else ''
        version = line['version'] if 'version' in line else ''
        cloud = line['cloud'] if 'cloud' in line else ''

        row = [dep_id, name, version, cloud]
        pretty_table.add_row(row)

    return pretty_table

def artifact_name_show(result, pretty_table):
    status_json = json.loads(result)
    app_status_list = status_json['data']

    logging.debug(app_status_list)

    for line in app_status_list:
        #name = line['name'] if 'name' in line else ''
        dep_id = line['dep_id'] if 'dep_id' in line else ''
        version = line['version'] if 'version' in line else ''
        cloud = line['cloud'] if 'cloud' in line else ''
        status = line['status'] if 'status' in line else ''
        artifact_info_dict = line['info'] if 'info' in line else {}

        artifact_info = ''
        if artifact_info_dict:
            for key, value in artifact_info_dict.iteritems():
                artifact_info = artifact_info + key + ": " + value + "\n"
        row = [dep_id, version, cloud, status, artifact_info]
        pretty_table.add_row(row)

    return pretty_table

def artifact_depid_show(result, pretty_table):
    status_json = json.loads(result)
    app_status_list = status_json['data']

    logging.debug(app_status_list)

    for line in app_status_list:
        name = line['name'] if 'name' in line else ''
        #dep_id = line['dep_id'] if 'dep_id' in line else ''
        version = line['version'] if 'version' in line else ''
        cloud = line['cloud'] if 'cloud' in line else ''
        status = line['status'] if 'status' in line else ''
        artifact_info_dict = line['info'] if 'info' in line else {}

        artifact_info = ''
        if artifact_info_dict:
            for key, value in artifact_info_dict.iteritems():
                artifact_info = artifact_info + key + ": " + value + "\n"
        row = [name, version, cloud, status, artifact_info]
        pretty_table.add_row(row)

    return pretty_table

def artifact_logs_show(result, pretty_table):
    status_json = json.loads(result)
    app_status = status_json['data']

    logging.debug(app_status)

    name = app_status['name']
    version = app_status['version']
    cloud = app_status['cloud']
    dep_log_loc = app_status['dep_log_location']
    run_log_loc = app_status['run_log_location']

    log_loc = dep_log_loc + "\n" + run_log_loc

    row = [name, version, cloud, log_loc]
    pretty_table.add_row(row)

    return pretty_table