'''
Created on Dec 13, 2016

@author: devdatta
'''
import logging
import os
import subprocess

from common import app
from common import docker_lib
from common import service
from common import utils
from manager.service_handler.mysql import google_handler as gh

TMP_LOG_FILE = "/tmp/lme-google-deploy-output.txt"

class GoogleDeployer(object):
    
    def __init__(self, task_def):
        self.task_def = task_def

        if task_def.app_data:
            self.app_dir = task_def.app_data['app_location']
            self.app_name = task_def.app_data['app_name']
            self.app_version = task_def.app_data['app_version']
            self.access_token_cont_name = "google-access-token-cont-" + self.app_name + "-" + self.app_version
            self.create_db_cont_name = "google-create-db-" + self.app_name + "-" + self.app_version
            self.app_obj = app.App(self.task_def.app_data)

        self.services = {}

        if task_def.service_data:
            self.service_obj = service.Service(task_def.service_data[0])
            if self.service_obj.get_service_type() == 'mysql':
                self.services['mysql'] = gh.MySQLServiceHandler(self.task_def)

            #self.service_details = task_def.service_data[0]['service_details']
            #if self.task_def.service_data[0]['service_type'] == 'mysql':
            #    self.services['mysql'] = gh.MySQLServiceHandler(self.task_def)

        self.docker_handler = docker_lib.DockerLib()

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
                        app_obj.update_app_status(line)
                if line.find("Deployed service [default] to") >= 0:
                    deployment_done = True
                    os.remove(TMP_LOG_FILE)

        return app_url

    def _cleanup(self, app_obj):
        # Remove any temporary container created for service provisioning
        for serv in self.task_def.service_data:
            serv_handler = self.services[serv['service']['type']]
            serv_handler.cleanup()

        # Remove app container
        self.docker_handler.remove_container(app_obj.get_cont_name(), "container created to deploy application no longer needed.")

    def deploy(self, deploy_type, deploy_name):
        if deploy_type == 'service':
            logging.debug("Google deployer called for deploying Google Cloud SQL service")

            service_ip_list = []
            for serv in self.task_def.service_data:
                serv_handler = self.services[serv['service']['type']]
                # Invoke public interface
                service_ip = serv_handler.provision_and_setup()
                service_ip_list.append(service_ip)

                utils.update_status(self.service_obj.get_status_file_location(), "Deployment complete")
                utils.update_ip(self.service_obj.get_status_file_location(), service_ip)

            # TODO(devkulkarni): Add support for returning multiple service IPs
            return service_ip_list[0]
        elif deploy_type == 'app':
            logging.debug("Google deployer called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status("DEPLOYING")
            app_ip_addr = self._deploy_app_container(app_obj)
            app_obj.update_app_status("DEPLOYMENT_COMPLETE")
            app_obj.update_app_ip(app_ip_addr)
            logging.debug("Google deployment complete.")
            logging.debug("Removing temporary containers created to assist in the deployment.")
            self._cleanup(app_obj)
        else:
            logging.debug("Unsupported deployment type specified.")