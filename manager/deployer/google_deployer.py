'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com>, December 13, 2016
'''

import logging
import logging.handlers as lh
import os
import subprocess
import time

from common import app
from common import docker_lib
from common import service
from common import utils
from common import constants
from common import fm_logger

from manager.service_handler.mysql import google_handler as gh

fmlogging = fm_logger.Logging()

TMP_LOG_FILE = "/tmp/lme-google-deploy-output.txt"

class GoogleDeployer(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        #self.logger = fmlogging.getLogger(name=self.__class__.__name__)
        #handler = lh.RotatingFileHandler(constants.LOG_FILE_NAME,
        #                                maxBytes=5000000, backupCount=0)
        #self.logger.addHandler(handler)

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

        self.docker_handler = docker_lib.DockerLib()

    def _download_logs(self, cont_id, logged_status):
        cwd = os.getcwd()
        fmlogging.debug("Current directory:%s" % cwd)
        for line in logged_status:
            if line.find("/root/.config/gcloud/logs") >=0:
                log_path = line.replace("[","").replace("]","")
                log_path = log_path[0:len(log_path)-1]
                src_log_file_name = log_path[log_path.rfind("/")+1:]
                log_file_name = self.app_version + constants.DEPLOY_LOG
                cp_cmd = ("docker cp {cont_id}:{log_path} .").format(cont_id=cont_id,
                                                                    log_path=log_path)
                os.system(cp_cmd)
                os.rename(src_log_file_name, log_file_name)
                return

    def _deploy_app_container(self, app_obj):
        app_cont_name = app_obj.get_cont_name()
        fmlogging.debug("Deploying app container:%s" % app_cont_name)

        docker_run_cmd = ("docker run {app_container}").format(app_container=app_cont_name)

        err = subprocess.Popen(docker_run_cmd, stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, shell=True).communicate()[1]

        logged_status = []

        app_url = ""
        done_reason = "TIMEOUT"

        log_lines = err.split("\n")
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
                done_reason = constants.APP_DEPLOYMENT_COMPLETE
            if line.find("ERROR") >=0:
                done_reason = constants.DEPLOYMENT_ERROR
                app_url = ""

        cont_id = ''
        try:
            docker_ps_cmd = ("docker ps -a | grep {app_container} | awk '{{print $1}}'").format(app_container=app_cont_name)
            cont_id = subprocess.check_output(docker_ps_cmd, shell=True)
            cont_id = cont_id.rstrip().lstrip()
        except Exception as e:
            fmlogging.error(e)

        self._download_logs(cont_id, logged_status)

        return app_url, done_reason

    def _cleanup(self, app_obj):
        # Remove any temporary container created for service provisioning
        for serv in self.task_def.service_data:
            serv_handler = self.services[serv['service']['type']]
            serv_handler.cleanup()

        # Remove app container
        self.docker_handler.stop_container(app_obj.get_cont_name(),
                                           "container created to deploy application no longer needed.")
        self.docker_handler.remove_container(app_obj.get_cont_name(),
                                             "container created to deploy application no longer needed.")
        self.docker_handler.remove_container_image(app_obj.get_cont_name(),
                                                   "container created to deploy application no longer needed.")

        # Remove any stray container
        self.docker_handler.stop_container("google", "Stopping google deployment related container")
        self.docker_handler.remove_container("google", "Removing google deployment related container")
        self.docker_handler.remove_container_image("google", "Removing google deployment related container image")

    def get_logs(self, info):
        fmlogging.debug("Google deployer called for getting app logs of app:%s" % info['app_name'])

    def deploy_for_delete(self, info):
        fmlogging.debug("Google deployer for called to delete app:%s" % info['app_name'])
        utils.delete(info)

    def deploy(self, deploy_type, deploy_name):
        if deploy_type == 'service':
            fmlogging.debug("Google deployer called for deploying Google Cloud SQL service")

            service_ip_list = []
            for serv in self.task_def.service_data:
                serv_handler = self.services[serv['service']['type']]

                utils.update_status(self.service_obj.get_status_file_location(),
                                    constants.DEPLOYING_SERVICE_INSTANCE)
                # Invoke public interface
                service_ip = serv_handler.provision_and_setup()
                service_ip_list.append(service_ip)

                utils.update_status(self.service_obj.get_status_file_location(),
                                    constants.SERVICE_INSTANCE_DEPLOYMENT_COMPLETE)
                utils.save_service_instance_ip(self.service_obj.get_status_file_location(),
                                               service_ip)

            # TODO(devkulkarni): Add support for returning multiple service IPs
            return service_ip_list[0]
        elif deploy_type == 'app':
            fmlogging.debug("Google deployer called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status(constants.DEPLOYING_APP)
            app_ip_addr, deployment_reason = self._deploy_app_container(app_obj)
            app_obj.update_app_status(deployment_reason)
            app_obj.update_app_ip(app_ip_addr)
            fmlogging.debug("Google deployment complete.")
            fmlogging.debug("Removing temporary containers created to assist in the deployment.")
            self._cleanup(app_obj)
        else:
            fmlogging.debug("Unsupported deployment type specified.")