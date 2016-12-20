'''
Created on Dec 13, 2016

@author: devdatta
'''
import logging
import os
import pexpect
import subprocess
import sys
import stat
import time

from docker import Client
from common import app
from common import docker_lib

TMP_LOG_FILE = "/tmp/lme-google-deploy-output.txt"

class GoogleDeployer(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.app_dir = task_def.app_data['app_location']
        self.app_name = task_def.app_data['app_name']
        self.app_version = task_def.app_data['app_version']
        self.access_token_cont_name = "google-access-token-cont-" + self.app_name + "-" + self.app_version
        self.create_db_cont_name = "google-create-db-" + self.app_name + "-" + self.app_version
        self.docker_handler = docker_lib.DockerLib()
        
    def _process_logs(self, cont_id, app_cont_name, app_obj):
        #docker_logs_cmd = ("docker logs {cont_id}").format(cont_id=cont_id)
        logging.debug("Fetching Docker logs")
        #logging.debug("Docker logs command:%s" % docker_logs_cmd)

        docker_run_cmd = ("docker run {app_container} >& {tmp_log_file}").format(app_container=app_cont_name,
                                                                                 tmp_log_file=TMP_LOG_FILE)
        logged_status = []
        app_url = "1.2.3.4"
        deployment_done = False

        #log_lines = subprocess.Popen(docker_run_cmd, stdout=subprocess.PIPE,
        #                             stderr=subprocess.PIPE, shell=True).communicate()[0]
        os.system(docker_run_cmd)
        fp = open("/tmp/lme-google-deploy-output.txt")
        while not deployment_done:
            #log_lines = subprocess.check_output(docker_run_cmd, shell=True)
            log_lines = fp.readlines()
            logging.debug("Log lines:%s" % log_lines)
            for line in log_lines:
                line = line.rstrip().lstrip()
                if line.find("Deployed URL") >= 0:
                    logged_status.append(line)
                    parts = line.split("[")
                    app_url = parts[1]
                    app_url = app_url[:-1].rstrip().lstrip()
                if line not in logged_status:
                        logged_status.append(line)
                        app_obj.update_app_status("status::" + line)
                if line.find("Deployed service [default] to") >= 0:
                    deployment_done = True
                    os.remove(TMP_LOG_FILE)
        return app_url

    def _deploy_app_container(self, app_obj):
        app_cont_name = app_obj.get_cont_name()        
        logging.debug("Deploying app container:%s" % app_cont_name)
        
        services = self.task_def.service_data
        cont_id = ''
        app_url = ''
        #if not services:
            #docker_run_cmd = ("docker run -i -t -d {app_container}").format(app_container=app_cont_name)
            #cont_id = subprocess.check_output(docker_run_cmd, shell=True)
            #logging.debug("Running container id:%s" % cont_id)
        
        app_url = self._process_logs(cont_id, app_cont_name, app_obj)
        return app_url

    def _deploy_service(self, access_token, project_id, db_server):
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

    def _create_db_user(self, access_token, project_id, db_server):

        self._wait_for_db_instance_to_get_ready(access_token, project_id, db_server)

        cmd = ('curl --header "Authorization: Bearer {access_token}" --header '
               '"Content-Type: application/json" --data \'{{"name":"lmeroot", "password":"lme123"}}\''
               ' https://www.googleapis.com/sql/v1beta4/projects/{project_id}/instances/{db_server}/users?host=%25&name=lmeroot -X PUT '
               ).format(access_token=access_token, db_server=db_server, project_id=project_id)
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

        for line in output.split("\n"):
            line = line.lstrip().rstrip()
            if line and line.startswith("\"ipAddress\""):
                components = line.split(":")
                ip_address = components[1].lstrip().rstrip()
                ip_address = ip_address.replace("\"",'')
                ip_address = ip_address.replace(",",'')
                logging.debug("*** IP Address:[%s]" % ip_address)
                return ip_address

    def _create_database_prev(self, db_ip, access_token, project_id, db_server):
        db_name = 'greetings'
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

        app_deploy_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir,
                                                         app_name=self.app_name)

        db_user = 'lmeroot'
        db_password = 'lme123'
        cmd = (" echo \" create database greetings \" | mysql -h{db_ip} --user={db_user} --password={db_password}  ").format(db_ip=db_ip,
                                                                                                                             db_user=db_user,
                                                                                                                             db_password=db_password)
        fp = open(app_deploy_dir + "/create-db.sh", "w")
        fp.write("#!/bin/sh \n")
        fp.write(cmd)
        fp.close()
        perm = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.chmod(app_deploy_dir + "/create-db.sh", perm)

        cwd = os.getcwd()
        os.chdir(app_deploy_dir)

        # Create Dockerfile
        df = ("FROM ubuntu:14.04 \n"
              "RUN apt-get update && apt-get install -y mysql-client-core-5.5\n"
              "COPY create-db.sh . \n"
              "CMD ./create-db.sh"
              )
        fp = open(app_deploy_dir + "/Dockerfile.create-db", "w")
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

        app_deploy_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir,
                                                         app_name=self.app_name)
        # Run the container
        cwd = os.getcwd()
        os.chdir(app_deploy_dir)
        docker_run_cmd = ("docker run -i -t -d {google_access_token_cont}").format(google_access_token_cont=self.access_token_cont_name)
        #cmd = "docker ps -a | grep google-access-token-cont | head -1 | cut -d ' ' -f 1"
        logging.debug(docker_run_cmd)

        cont_id = subprocess.check_output(docker_run_cmd, shell=True).rstrip().lstrip()
        logging.debug("Container id:%s" % cont_id)

        copy_file_cmd = ("docker cp {cont_id}:/src/access_token.txt {access_token_path}").format(cont_id=cont_id,
                                                                                                 access_token_path=app_deploy_dir+ "/access_token.txt")
        logging.debug("Copy command:%s" % copy_file_cmd)
        os.system(copy_file_cmd)

        access_token_fp = open(app_deploy_dir + "/access_token.txt/access_token.txt")
        access_token = access_token_fp.read().rstrip().lstrip()
        logging.debug("Obtained access token:%s" % access_token)
        os.remove(app_deploy_dir + "/access_token.txt/access_token.txt")
        os.removedirs(app_deploy_dir + "/access_token.txt")

        # Stop and remove container generated for obtaining new access_token
        self.docker_handler.stop_container(self.access_token_cont_name, "access token container no longer needed")
        self.docker_handler.remove_container(self.access_token_cont_name, "access token container no longer needed")
        self.docker_handler.remove_container_image(self.access_token_cont_name, "access token container no longer needed")

        os.chdir(cwd)
        return access_token

    def _cleanup(self, app_obj):
        # Stop and remove container generated for creating the database
        self.docker_handler.stop_container(self.create_db_cont_name, "container created to create db no longer needed.")
        self.docker_handler.remove_container(self.create_db_cont_name, "container created to create db no longer needed.")
        self.docker_handler.remove_container_image(self.create_db_cont_name, "container created to create db no longer needed.")

        # Remove app container
        self.docker_handler.remove_container(app_obj.get_cont_name(), "container created to deploy application no longer needed.")

    def deploy(self, deploy_type, deploy_name):
        if deploy_type == 'service':
            logging.debug("Google deployer called for deploying Google Cloud SQL service for app %s" %
                          self.task_def.app_data['app_name'])
            access_token = self._parse_access_token()
            db_server = self.app_name + "-" + self.app_version + "-db-instance"
            project_id = self.task_def.app_data['project_id']
            self._deploy_service(access_token, project_id, db_server)
            self._create_db_user(access_token, project_id, db_server)
            service_ip = self._get_ip_address_of_db(access_token, project_id, db_server)
            self._create_database(service_ip)
            return service_ip
        elif deploy_type == 'app':
            logging.debug("Google deployer called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status("status::DEPLOYING")
            app_ip_addr = self._deploy_app_container(app_obj)
            app_obj.update_app_status("status::DEPLOYMENT_COMPLETE")
            app_obj.update_app_ip(app_ip_addr)
            logging.debug("Google deployment complete.")
            logging.debug("Removing temporary containers created to assist in the deployment.")
            self._cleanup(app_obj)
        else:
            logging.debug("Unsupported deployment type specified.")