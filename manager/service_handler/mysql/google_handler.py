'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com>, December 22, 2016
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
from common import fm_logger

fmlogging = fm_logger.Logging()


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

        # Check if we have already provisioned a db instance. If so, use that password
        password = self._read_password()
        if not password:
            self.mysql_password = utils.generate_google_password()
        else:
            self.mysql_password = password

        self.db_info = {}

        self.db_info['user'] = self.mysql_user
        self.db_info['db'] = self.mysql_db_name
        self.db_info['password'] = self.mysql_password

        self.docker_handler = docker_lib.DockerLib()

    def _read_password(self):
        password = ''
        path = ''
        if hasattr(self, 'service_obj'):
            path = self.service_obj.get_service_details_file_location()
        if path and os.path.exists(path):
            password = utils.read_password(path)
        return password

    def _restrict_db_access(self, access_token, project_id, db_server, settings_version):
        cmd = ('curl --header "Authorization: Bearer {access_token}" --header '
               '"Content-Type: application/json" --data \'{{"name":"{db_server}",'
               '"region":"us-central", "settings": {{"settingsVersion":"{version}", "tier":"db-n1-standard-1", "activationPolicy":"ALWAYS", "ipConfiguration":{{"authorizedNetworks":[]}}}}}}\' '
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server} -X PUT').format(access_token=access_token,
                                                                                                                    db_server=db_server,
                                                                                                                    version=settings_version,
                                                                                                                    project_id=project_id)
        fmlogging.debug("Restricting access to Cloud SQL instance")
        fmlogging.debug(cmd)
        err, output = utils.execute_shell_cmd(cmd)

        if output.lower().find("error") >= 0:
            fmlogging.error("Error occurred in restricting access to Cloud SQL instance. %s" % output)
            raise Exception()

        self._wait_for_db_instance_to_get_ready(access_token, project_id, db_server)

    def _store_settings_version(self, settings_version):
        # Save settings_version
        fp = open(self.instance_prov_workdir + "/settings_version.txt", "w")
        fp.write(settings_version)
        fp.flush()
        fp.close()

    def _deploy_instance(self, access_token, project_id, db_server):
        cmd = ('curl --header "Authorization: Bearer {access_token}" --header '
               '"Content-Type: application/json" --data \'{{"name":"{db_server}",'
               '"region":"us-central", "settings": {{"tier":"db-n1-standard-1", "activationPolicy":"ALWAYS", "ipConfiguration":{{"authorizedNetworks":[{{"value":"0.0.0.0/0"}}]}}}}}}\' '
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances -X POST').format(access_token=access_token,
                                                                                                        db_server=db_server,
                                                                                                        project_id=project_id)
        fmlogging.debug("Creating Cloud SQL instance")
        fmlogging.debug(cmd)
        try:
            os.system(cmd)
        except Exception as e:
            print(e)

        settings_version = self._wait_for_db_instance_to_get_ready(access_token, project_id, db_server)
        self._store_settings_version(settings_version)
        return settings_version

    def _get_settings_version(self, instance_name, instance_version):
        service_dir_path = constants.SERVICE_STORE_PATH + "/" + instance_name + "/" + instance_version
        fp = open(service_dir_path + "/settings_version.txt", "r")
        settings_version = fp.read()
        settings_version = settings_version.rstrip().lstrip()
        return settings_version

    def _create_user(self, access_token, project_id, db_server):
        # TODO(devkulkarni): Need to read these values from a configuration file
        username_val = constants.DEFAULT_DB_USER
        password_val = self.db_info['password']
        cmd = ('curl --header "Authorization: Bearer {access_token}" --header '
               '"Content-Type: application/json" --data \'{{"name":"{username_val}", "password":"{password_val}"}}\''
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server}/users?host=%25&name={username_val} -X PUT '
               ).format(access_token=access_token, db_server=db_server, project_id=project_id,
                        username_val=username_val, password_val=password_val)
        fmlogging.debug("Setting Cloud SQL credentials")
        fmlogging.debug(cmd)
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
                fmlogging.debug("Link for tracking create user operation:%s" % self_link)

        if self_link:
            user_created = False
            track_usr_cmd = ('curl --header "Authorization: Bearer {access_token}" '
                             ' {track_op} -X GET').format(access_token=access_token, track_op=self_link)
            fmlogging.debug("Track user create operation cmd:%s" % track_usr_cmd)
            fmlogging.debug(track_usr_cmd)

            while not user_created:
                try:
                    output = subprocess.Popen(track_usr_cmd, stdout=subprocess.PIPE,
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

            fmlogging.debug("Creating user done.")

        # Save Cloud SQL instance information
        fp = open(self.service_obj.get_service_details_file_location(), "w")
        fp.write("%s::%s\n" % (constants.DB_NAME, constants.DEFAULT_DB_NAME))
        fp.write("%s::%s\n" % (constants.DB_USER, constants.DEFAULT_DB_USER))
        fp.write("%s::%s\n" % (constants.DB_USER_PASSWORD, password_val))

    def _wait_for_db_instance_to_get_ready(self, access_token, project_id, db_server):
        cmd = ('curl --header "Authorization: Bearer {access_token}" '
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server} -X GET'
              ).format(access_token=access_token, project_id=project_id, db_server=db_server)

        fmlogging.debug("Track google cloud sql create status")
        fmlogging.debug("cmd:%s" % cmd)

        settings_version = ''
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
                if line and line.find("\"settingsVersion\"") >= 0:
                    components = line.split(":")
                    settings_version = components[1].replace('"','').replace(',','')
                    settings_version = settings_version.rstrip().lstrip()
            time.sleep(2)
        return settings_version

    def _get_connection_endpoints_of_db(self, access_token, project_id, db_server):
        cmd = ('curl --header "Authorization: Bearer {access_token}" '
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server} -X GET'
              ).format(access_token=access_token, project_id=project_id, db_server=db_server)
        fmlogging.debug("Obtaining IP address of the Cloud SQL instance")
        fmlogging.debug(cmd)
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
            fmlogging.debug("*** Parsed entity:[%s]" % entity)
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
                self.connection_name = '/cloudsql/' + self.connection_name
            if line and line.startswith("\"tier\""):
                self.database_tier = _parse_entity(line)

        return ip_address, self.connection_name

    def _create_database_prev(self, db_ip, access_token, project_id, db_server):
        db_name = constants.DEFAULT_DB_NAME
        cmd = ('curl --header "Authorization: Bearer {access_token}" '
               '"Content-Type: application/json" --data \'{{"instance":"{db_server}", "name":"{db_name}", "project":"{project_id}"}}\''
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server}/databases -X POST'
              ).format(access_token=access_token, project_id=project_id, db_server=db_server, db_name=db_name)
        fmlogging.debug("Creating database")
        fmlogging.debug(cmd)
        try:
            output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True).communicate()[0]
        except Exception as e:
            print(e)

    def _create_database(self, db_ip):
        fmlogging.debug("Creating database")

        deploy_dir = ("{instance_dir}/{instance_name}").format(instance_dir=self.instance_prov_workdir,
                                                               instance_name=self.instance_name)

        # Read these values from lme.conf file
        db_user = constants.DEFAULT_DB_USER
        db_password = self.db_info['password']
        db_name = constants.DEFAULT_DB_NAME
        cmd = (" echo \" create database {db_name} \" | mysql -h{db_ip} --user={db_user} --password='{db_password}'").format(db_ip=db_ip,
                                                                                                                             db_user=db_user,
                                                                                                                             db_password=db_password,
                                                                                                                             db_name=db_name)
        fp = open(deploy_dir + "/create-db.sh", "w")
        fp.write("#!/bin/sh \n")
        fp.write(cmd)
        fp.close()
        perm = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.chmod(deploy_dir + "/create-db.sh", perm)

        #cwd = os.getcwd()
        #os.chdir(deploy_dir)

        # Create Dockerfile to execute the script that creates the database
        df = ("FROM lmecld/clis:mysql-client-5.5 \n"
              "COPY create-db.sh . \n"
              "CMD ./create-db.sh"
              )
        fp = open(deploy_dir + "/Dockerfile.create-db", "w")
        fp.write(df)
        fp.close()

        docker_build_cmd = ("docker build -t {create_db_cont_name} -f {deploy_dir}/Dockerfile.create-db {deploy_dir}").format(create_db_cont_name=self.create_db_cont_name,
                                                                                                                              deploy_dir=deploy_dir)
        fmlogging.debug("Docker build cmd for database create cont:%s" % docker_build_cmd)
        os.system(docker_build_cmd)

        docker_run_cmd = ("docker run -i -t -d {create_db_cont_name}").format(create_db_cont_name=self.create_db_cont_name)
        fmlogging.debug("Docker run cmd for database create cont:%s" % docker_run_cmd)
        os.system(docker_run_cmd)

        #os.chdir(cwd)

    def _parse_access_token(self):
        fmlogging.debug("Parsing Google access token")

        deploy_dir = ("{instance_dir}/{instance_name}").format(instance_dir=self.instance_prov_workdir,
                                                               instance_name=self.instance_name)
        # Run the container
        #cwd = os.getcwd()
        #os.chdir(deploy_dir)

        docker_run_cmd = ("docker run -i -t -d {google_access_token_cont}").format(google_access_token_cont=self.access_token_cont_name)
        fmlogging.debug(docker_run_cmd)

        cont_id = subprocess.check_output(docker_run_cmd, shell=True).rstrip().lstrip()
        fmlogging.debug("Container id:%s" % cont_id)

        copy_file_cmd = ("docker cp {cont_id}:/src/access_token.txt {access_token_path}").format(cont_id=cont_id,
                                                                                                 access_token_path=deploy_dir+ "/.")
        fmlogging.debug("Copy command:%s" % copy_file_cmd)
        os.system(copy_file_cmd)

        access_token_fp = open(deploy_dir + "/access_token.txt")
        access_token = access_token_fp.read().rstrip().lstrip()
        fmlogging.debug("Obtained access token:%s" % access_token)

        # Stop and remove container generated for obtaining new access_token
        self.docker_handler.stop_container(self.access_token_cont_name, "access token container no longer needed")
        self.docker_handler.remove_container(self.access_token_cont_name, "access token container no longer needed")
        self.docker_handler.remove_container_image(self.access_token_cont_name, "access token container no longer needed")

        #os.chdir(cwd)
        return access_token

    def _generate_docker_file_to_obtain_access_token(self):
        fmlogging.debug("Generating Docker file that will give new access token.")
        if self.service_obj:
            utils.update_status(self.service_obj.get_status_file_location(),
                                "GENERATING Google ARTIFACTS for MySQL service")

        deploy_dir = ("{instance_dir}/{instance_name}").format(instance_dir=self.instance_prov_workdir,
                                                               instance_name=self.instance_name)
        utils.copy_google_creds(constants.GOOGLE_CREDS_PATH, deploy_dir)

        cmd_1 = ("RUN sed -i 's/{pat}access_token{pat}.*/{pat}access_token{pat}/' credentials \n").format(pat="\\\"")
        df = ("FROM lmecld/clis:gcloud \n"
              "COPY . /src \n"
              "COPY google-creds/gcloud  /root/.config/gcloud \n"
              "WORKDIR /root/.config/gcloud \n"
              "RUN token=`/google-cloud-sdk/bin/gcloud beta auth application-default print-access-token` && \ \n"
              "    echo $token > /src/access_token.txt"
            ).format(cmd_1=cmd_1)

        fp = open(deploy_dir + "/Dockerfile.access_token", "w")
        fp.write(df)
        fp.close()

    def _build_access_token_container(self):
        fmlogging.debug("Building service container")
        deploy_dir = ("{instance_dir}/{instance_name}").format(instance_dir=self.instance_prov_workdir,
                                                               instance_name=self.instance_name)
        #cwd = os.getcwd()
        #os.chdir(deploy_dir)
        cmd = ("docker build -t {google_access_token_cont} -f {deploy_dir}/Dockerfile.access_token {deploy_dir} ").format(google_access_token_cont=self.access_token_cont_name,
                                                                                                                          deploy_dir=deploy_dir)
        try:
            os.system(cmd)
        except Exception as e:
            print(e)
        #os.chdir(cwd)

    def _save_instance_information(self, instance_ip):

        fp = open(self.service_obj.get_service_details_file_location(), "a")
        fp.write("%s::%s\n" % (constants.CLOUD_SQL_CONNECTION_STR, self.connection_name))
        fp.write("%s::%s\n" % (constants.MYSQL_VERSION, self.database_version))
        fp.write("%s::%s\n" % (constants.CLOUD_SQL_TIER, self.database_tier))
        fp.close()

        if self.app_status_file:
            fp = open(self.app_status_file, "a")
            fp.write("%s::%s, " % (constants.CLOUD_SQL_INSTANCE, instance_ip))
            fp.write("%s::%s, " % (constants.DB_NAME, constants.DEFAULT_DB_NAME))
            fp.write("%s::%s, " % (constants.DB_USER, constants.DEFAULT_DB_USER))
            fp.write("%s::%s, " % (constants.DB_USER_PASSWORD, self.db_info['password']))
            fp.close()

    # Public interface
    def provision_and_setup(self):
        db_server = self.instance_name + "-" + self.instance_version + "-db-instance"
        project_id = self.task_def.cloud_data['project_id']
        access_token = self._parse_access_token()
        settings_version = self._deploy_instance(access_token, project_id, db_server)
        self._create_user(access_token, project_id, db_server)
        service_ip, connection_name = self._get_connection_endpoints_of_db(access_token, project_id, db_server)
        self._create_database(service_ip)
        self._save_instance_information(service_ip)
        if self.task_def.service_data[0]['lock'] == 'true':
            self._restrict_db_access(access_token, project_id, db_server, settings_version)
            return connection_name
        else:
            return service_ip

    def make_secure(self, project_id, info):
        service_name = info['service_name']
        service_version = info['service_version']
        fmlogging.debug("Making instance %s-%s secure" % (service_name, service_version))
        db_server = service_name + "-" + service_version + "-db-instance"
        self.instance_name = service_name
        self.instance_prov_workdir = constants.SERVICE_STORE_PATH + "/" + service_name + "/" + service_version
        self.access_token_cont_name = "google-access-token-cont-" + self.instance_name + "-" + service_version
        self._build_access_token_container()
        access_token = self._parse_access_token()
        settings_version = self._get_settings_version(service_name, service_version)
        self._restrict_db_access(access_token, project_id, db_server, settings_version)
        settings_version = self._wait_for_db_instance_to_get_ready(access_token, project_id, db_server)
        self._store_settings_version(settings_version)

    def generate_instance_artifacts(self):
        self._generate_docker_file_to_obtain_access_token()

    def get_terminate_cmd(self, info):
        service_version = info['service_version']
        service_name = info['service_name']
        instance_name = ("{service_name}-{service_version}-db-instance").format(service_name=service_name,
                                                                                service_version=service_version)
        delete_cmd = ("/google-cloud-sdk/bin/gcloud sql instances delete {instance_name} --quiet").format(instance_name=instance_name)

        return delete_cmd

    def build_instance_artifacts(self):
        self._build_access_token_container()

    def cleanup(self):
        # Stop and remove container generated for creating the database
        if self.task_def.service_data:
            self.docker_handler.stop_container(self.create_db_cont_name, "container created to create db no longer needed.")
            self.docker_handler.remove_container(self.create_db_cont_name, "container created to create db no longer needed.")
            self.docker_handler.remove_container_image(self.create_db_cont_name, "container created to create db no longer needed.")

    def get_instance_info(self):
        return self.db_info