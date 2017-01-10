'''
Created on Dec 22, 2016

@author: devdatta
'''
import logging
import os
import stat
import subprocess
import time

from common import docker_lib
from common import service
from common import utils
from common import constants


class MySQLServiceHandler(object):

    def __init__(self, task_def):
        self.task_def = task_def
        self.instance_name = ''
        self.instance_version = ''
        self.instance_prov_workdir = ''
        self.connection_name = ''
        self.database_version = ''
        self.database_tier = ''
        self.instance_ip_address = ''
        self.app_status_file = ''
        if task_def.app_data:
            self.instance_prov_workdir = task_def.app_data['app_location']
            self.instance_name = task_def.app_data['app_name']
            self.instance_version = task_def.app_data['app_version']
            self.access_token_cont_name = "google-access-token-cont-" + self.instance_name + "-" + self.instance_version
            self.create_db_cont_name = "google-create-db-" + self.instance_name + "-" + self.instance_version
            self.app_status_file = constants.APP_STORE_PATH + "/" + self.instance_name + "/" + self.instance_version + "/app-status.txt"
        if task_def.service_data:
            self.service_obj = service.Service(task_def.service_data[0])
            self.instance_prov_workdir = self.service_obj.get_service_prov_work_location()
            self.instance_name = self.service_obj.get_service_name()
            self.instance_version = self.service_obj.get_service_version()
            self.access_token_cont_name = "google-access-token-cont-" + self.instance_name + "-" + self.instance_version
            self.create_db_cont_name = "google-create-db-" + self.instance_name + "-" + self.instance_version

        self.mysql_db_name = constants.DEFAULT_DB_NAME
        self.mysql_user = constants.DEFAULT_DB_USER
        self.mysql_password = constants.DEFAULT_DB_PASSWORD

        self.db_info = {}

        self.db_info['user'] = self.mysql_user
        self.db_info['password'] = self.mysql_password
        self.db_info['db'] = self.mysql_db_name

        self.docker_handler = docker_lib.DockerLib()

    def _deploy_instance(self, access_token, project_id, db_server):
        cmd = ('curl --header "Authorization: Bearer {access_token}" --header '
               '"Content-Type: application/json" --data \'{{"name":"{db_server}",'
               '"region":"us-central", "settings": {{"tier":"db-n1-standard-1", "activationPolicy":"ALWAYS", "ipConfiguration":{{"authorizedNetworks":[{{"value":"0.0.0.0/0"}}]}}}}}}\' '
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances -X POST').format(access_token=access_token,
                                                                                                        db_server=db_server,
                                                                                                        project_id=project_id)
        logging.debug("Creating Cloud SQL instance")
        logging.debug(cmd)
        try:
            os.system(cmd)
        except Exception as e:
            print(e)

        self._wait_for_db_instance_to_get_ready(access_token, project_id, db_server)

    def _create_user(self, access_token, project_id, db_server):
        # TODO(devkulkarni): Need to read these values from a configuration file
        username_val = constants.DEFAULT_DB_USER
        password_val = constants.DEFAULT_DB_PASSWORD
        cmd = ('curl --header "Authorization: Bearer {access_token}" --header '
               '"Content-Type: application/json" --data \'{{"name":"{username_val}", "password":"{password_val}"}}\''
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server}/users?host=%25&name={username_val} -X PUT '
               ).format(access_token=access_token, db_server=db_server, project_id=project_id,
                        username_val=username_val, password_val=password_val)
        logging.debug("Setting Cloud SQL credentials")
        logging.debug(cmd)
        try:
            output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, shell=True).communicate()[0]
        except Exception as e:
            print(e)

        self_link = ''
        for line in output.split("\n"):
            line = line.lstrip().rstrip()
            if line and line.find("selfLink") >= 0:
                parts = line.split(" ")
                self_link = parts[1].rstrip().lstrip()
                self_link = self_link.replace(",","").replace("\"","")
                logging.debug("Link for tracking create user operation:%s" % self_link)

        if self_link:
            user_created = False
            track_usr_cmd = ('curl --header "Authorization: Bearer {access_token}" '
                             ' {track_op} -X GET').format(access_token=access_token, track_op=self_link)
            logging.debug("Track user create operation cmd:%s" % track_usr_cmd)
            logging.debug(track_usr_cmd)

            while not user_created:
                try:
                    output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE, shell=True).communicate()[0]
                except Exception as e:
                    print(e)
                for line in output.split("\n"):
                    line = line.lstrip().rstrip()
                    if line and line.find("status") >= 0:
                        parts = line.split(" ")
                        is_done = parts[1].rstrip().lstrip()
                        if is_done.find("DONE") >= 0:
                            user_created = True
                time.sleep(2)

            logging.debug("Creating user done.")

    def _wait_for_db_instance_to_get_ready(self, access_token, project_id, db_server):
        cmd = ('curl --header "Authorization: Bearer {access_token}" '
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server} -X GET'
              ).format(access_token=access_token, project_id=project_id, db_server=db_server)

        db_instance_up = False
        while not db_instance_up:
            try:
                output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, shell=True).communicate()[0]
            except Exception as e:
                print(e)

            for line in output.split("\n"):
                line = line.lstrip().rstrip()
                if line and line.startswith("\"state\""):
                    components = line.split(":")
                    status = components[1].lstrip().rstrip()
                    if status.find('RUNNABLE') >= 0:
                        db_instance_up = True
            time.sleep(2)

    def _get_ip_address_of_db(self, access_token, project_id, db_server):
        cmd = ('curl --header "Authorization: Bearer {access_token}" '
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server} -X GET'
              ).format(access_token=access_token, project_id=project_id, db_server=db_server)
        logging.debug("Obtaining IP address of the Cloud SQL instance")
        logging.debug(cmd)
        try:
            output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True).communicate()[0]
        except Exception as e:
            print(e)

        def _parse_entity(line):
            components = line.split(" ")
            entity = components[1].lstrip().rstrip()
            entity = entity.replace("\"",'')
            entity = entity.replace(",",'')
            logging.debug("*** Parsed entity:[%s]" % entity)
            return entity

        for line in output.split("\n"):
            line = line.lstrip().rstrip()
            if line and line.startswith("\"ipAddress\""):
                ip_address = _parse_entity(line)
                self.instance_ip_address = ip_address
            if line and line.startswith("\"databaseVersion\""):
                self.database_version = _parse_entity(line)
            if line and line.startswith("\"connectionName\""):
                self.connection_name = _parse_entity(line)
            if line and line.startswith("\"tier\""):
                self.database_tier = _parse_entity(line)

        return ip_address

    def _create_database_prev(self, db_ip, access_token, project_id, db_server):
        db_name = constants.DEFAULT_DB_NAME
        cmd = ('curl --header "Authorization: Bearer {access_token}" '
               '"Content-Type: application/json" --data \'{{"instance":"{db_server}", "name":"{db_name}", "project":"{project_id}"}}\''
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server}/databases -X POST'
              ).format(access_token=access_token, project_id=project_id, db_server=db_server, db_name=db_name)
        logging.debug("Creating database")
        logging.debug(cmd)
        try:
            output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True).communicate()[0]
        except Exception as e:
            print(e)

    def _create_database(self, db_ip):
        logging.debug("Creating database")

        deploy_dir = ("{instance_dir}/{instance_name}").format(instance_dir=self.instance_prov_workdir,
                                                               instance_name=self.instance_name)

        # Read these values from lme.conf file
        db_user = constants.DEFAULT_DB_USER
        db_password = constants.DEFAULT_DB_PASSWORD
        db_name = constants.DEFAULT_DB_NAME
        cmd = (" echo \" create database {db_name} \" | mysql -h{db_ip} --user={db_user} --password={db_password}  ").format(db_ip=db_ip,
                                                                                                                             db_user=db_user,
                                                                                                                             db_password=db_password,
                                                                                                                             db_name=db_name)
        fp = open(deploy_dir + "/create-db.sh", "w")
        fp.write("#!/bin/sh \n")
        fp.write(cmd)
        fp.close()
        perm = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.chmod(deploy_dir + "/create-db.sh", perm)

        cwd = os.getcwd()
        os.chdir(deploy_dir)

        # Create Dockerfile to execute the script that creates the database
        df = ("FROM ubuntu:14.04 \n"
              "RUN apt-get update && apt-get install -y mysql-client-core-5.5\n"
              "COPY create-db.sh . \n"
              "CMD ./create-db.sh"
              )
        fp = open(deploy_dir + "/Dockerfile.create-db", "w")
        fp.write(df)
        fp.close()

        docker_build_cmd = ("docker build -t {create_db_cont_name} -f Dockerfile.create-db .").format(create_db_cont_name=self.create_db_cont_name)
        logging.debug("Docker build cmd for database create cont:%s" % docker_build_cmd)
        os.system(docker_build_cmd)

        docker_run_cmd = ("docker run -i -t -d {create_db_cont_name}").format(create_db_cont_name=self.create_db_cont_name)
        logging.debug("Docker run cmd for database create cont:%s" % docker_run_cmd)
        os.system(docker_run_cmd)

        os.chdir(cwd)

    def _parse_access_token(self):
        logging.debug("Parsing Google access token")

        deploy_dir = ("{instance_dir}/{instance_name}").format(instance_dir=self.instance_prov_workdir,
                                                               instance_name=self.instance_name)
        # Run the container
        cwd = os.getcwd()
        os.chdir(deploy_dir)
        docker_run_cmd = ("docker run -i -t -d {google_access_token_cont}").format(google_access_token_cont=self.access_token_cont_name)
        logging.debug(docker_run_cmd)

        cont_id = subprocess.check_output(docker_run_cmd, shell=True).rstrip().lstrip()
        logging.debug("Container id:%s" % cont_id)

        copy_file_cmd = ("docker cp {cont_id}:/src/access_token.txt {access_token_path}").format(cont_id=cont_id,
                                                                                                 access_token_path=deploy_dir+ "/access_token.txt")
        logging.debug("Copy command:%s" % copy_file_cmd)
        os.system(copy_file_cmd)

        access_token_fp = open(deploy_dir + "/access_token.txt/access_token.txt")
        access_token = access_token_fp.read().rstrip().lstrip()
        logging.debug("Obtained access token:%s" % access_token)
        os.remove(deploy_dir + "/access_token.txt/access_token.txt")
        os.removedirs(deploy_dir + "/access_token.txt")

        # Stop and remove container generated for obtaining new access_token
        self.docker_handler.stop_container(self.access_token_cont_name, "access token container no longer needed")
        self.docker_handler.remove_container(self.access_token_cont_name, "access token container no longer needed")
        self.docker_handler.remove_container_image(self.access_token_cont_name, "access token container no longer needed")

        os.chdir(cwd)
        return access_token

    def _generate_docker_file_to_obtain_access_token(self):
        logging.debug("Generating Docker file that will give new access token.")
        utils.update_status(self.service_obj.get_status_file_location(),
                            "GENERATING Google ARTIFACTS for MySQL service")

        deploy_dir = ("{instance_dir}/{instance_name}").format(instance_dir=self.instance_prov_workdir,
                                                               instance_name=self.instance_name)
        utils.copy_google_creds(constants.GOOGLE_CREDS_PATH, deploy_dir)

        cmd_1 = ("RUN sed -i 's/{pat}access_token{pat}.*/{pat}access_token{pat}/' credentials \n").format(pat="\\\"")
        df = ("FROM ubuntu:14.04 \n"
              "RUN apt-get update && apt-get install -y wget python \n"
              "RUN sudo wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-126.0.0-linux-x86_64.tar.gz && \ \n"
              "    sudo gunzip google-cloud-sdk-126.0.0-linux-x86_64.tar.gz && \ \n"
              "    sudo tar -xvf google-cloud-sdk-126.0.0-linux-x86_64.tar \n"
              "RUN /google-cloud-sdk/bin/gcloud components install beta \n"
              "COPY . /src \n"
              "COPY google-creds/gcloud  /root/.config/gcloud \n"
              "WORKDIR /root/.config/gcloud \n"
              "RUN token=`/google-cloud-sdk/bin/gcloud beta auth application-default print-access-token` && \ \n"
              "    echo $token > /src/access_token.txt"
            ).format(cmd_1=cmd_1)

        fp = open(deploy_dir + "/Dockerfile.access_token", "w")
        fp.write(df)
        fp.close()

    def _build_service_container(self):
        logging.debug("Building service container")
        deploy_dir = ("{instance_dir}/{instance_name}").format(instance_dir=self.instance_prov_workdir,
                                                               instance_name=self.instance_name)
        cwd = os.getcwd()
        os.chdir(deploy_dir)
        cmd = ("docker build -t {google_access_token_cont} -f Dockerfile.access_token . ").format(google_access_token_cont=self.access_token_cont_name)
        try:
            os.system(cmd)
        except Exception as e:
            print(e)
        os.chdir(cwd)

    def _save_instance_information(self, instance_ip):
        fp = open(self.service_obj.get_service_details_file_location(), "w")

        fp.write("%s::%s\n" % (constants.DB_NAME, constants.DEFAULT_DB_NAME))
        fp.write("%s::%s\n" % (constants.DB_USER, constants.DEFAULT_DB_USER))
        fp.write("%s::%s\n" % (constants.DB_USER_PASSWORD, constants.DEFAULT_DB_PASSWORD))

        fp.write("%s::%s\n" % (constants.CLOUD_SQL_CONNECTION_STR, self.connection_name))
        fp.write("%s::%s\n" % (constants.MYSQL_VERSION, self.database_version))
        fp.write("%s::%s\n" % (constants.CLOUD_SQL_TIER, self.database_tier))
        fp.close()

        if self.app_status_file:
            fp = open(self.app_status_file, "a")
            fp.write("%s::%s, " % (constants.CLOUD_SQL_INSTANCE, instance_ip))
            fp.write("%s::%s, " % (constants.DB_NAME, constants.DEFAULT_DB_NAME))
            fp.write("%s::%s, " % (constants.DB_USER, constants.DEFAULT_DB_USER))
            fp.write("%s::%s, " % (constants.DB_USER_PASSWORD, constants.DEFAULT_DB_PASSWORD))
            fp.close()

    # Public interface
    def provision_and_setup(self):
        db_server = self.instance_name + "-" + self.instance_version + "-db-instance"
        project_id = self.task_def.cloud_data['project_id']
        access_token = self._parse_access_token()
        self._deploy_instance(access_token, project_id, db_server)
        self._create_user(access_token, project_id, db_server)
        service_ip = self._get_ip_address_of_db(access_token, project_id, db_server)
        self._create_database(service_ip)
        self._save_instance_information(service_ip)
        return service_ip

    def generate_instance_artifacts(self):
        self._generate_docker_file_to_obtain_access_token()

    def build_instance_artifacts(self):
        self._build_service_container()

    def cleanup(self):
        # Stop and remove container generated for creating the database
        if self.task_def.service_data:
            self.docker_handler.stop_container(self.create_db_cont_name, "container created to create db no longer needed.")
            self.docker_handler.remove_container(self.create_db_cont_name, "container created to create db no longer needed.")
            self.docker_handler.remove_container_image(self.create_db_cont_name, "container created to create db no longer needed.")

    def get_instance_info(self):
        return self.db_info