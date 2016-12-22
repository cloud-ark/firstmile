'''
Created on Dec 13, 2016

@author: devdatta
'''
import logging
import os
import subprocess

from common import app
from common import docker_lib
from manager.service_handler.mysql import google_handler as gh

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
        self.app_obj = app.App(self.task_def.app_data)

        self.services = {}

        if task_def.service_data:
            self.service_details = task_def.service_data[0]['service_details']
            if self.task_def.service_data[0]['service_type'] == 'mysql':
                self.services['mysql'] = gh.MySQLServiceHandler(self.task_def, self.app_obj)

    def _deploy_app_container(self, app_obj):
        app_cont_name = app_obj.get_cont_name()
        logging.debug("Deploying app container:%s" % app_cont_name)
        docker_run_cmd = ("docker run {app_container} >& {tmp_log_file}").format(app_container=app_cont_name,
                                                                                 tmp_log_file=TMP_LOG_FILE)
        logged_status = []

        deployment_done = False

        os.system(docker_run_cmd)
        fp = open(TMP_LOG_FILE)
        app_url = ""
        while not deployment_done:
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

    def _parse_access_token(self):
        logging.debug("Parsing Google access token")

        app_deploy_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir,
                                                         app_name=self.app_name)
        # Run the container
        cwd = os.getcwd()
        os.chdir(app_deploy_dir)
        docker_run_cmd = ("docker run -i -t -d {google_access_token_cont}").format(google_access_token_cont=self.access_token_cont_name)
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
        # Remove any temporary container created for service provisioning
        for serv in self.task_def.service_data:
            serv_handler = self.services[serv['service_type']]
            serv_handler.cleanup()

        # Remove app container
        self.docker_handler.remove_container(app_obj.get_cont_name(), "container created to deploy application no longer needed.")

    def deploy(self, deploy_type, deploy_name):
        if deploy_type == 'service':
            logging.debug("Google deployer called for deploying Google Cloud SQL service for app %s" %
                          self.task_def.app_data['app_name'])
            access_token = self._parse_access_token()

            service_ip_list = []
            for serv in self.task_def.service_data:
                serv_handler = self.services[serv['service_type']]
                # Invoke public interface
                service_ip = serv_handler.provision_and_setup(access_token)
                service_ip_list.append(service_ip)

            # TODO(devkulkarni): Add support for returning multiple service IPs
            return service_ip_list[0]
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