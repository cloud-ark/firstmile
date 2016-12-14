'''
Created on Dec 13, 2016

@author: devdatta
'''
import logging
import os
import pexpect
import subprocess
import sys
import time

from docker import Client
from common import app

class GoogleDeployer(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        
    def _process_logs(self, cont_id, app_cont_name, app_obj):
        #docker_logs_cmd = ("docker logs {cont_id}").format(cont_id=cont_id)
        logging.debug("Fetching Docker logs")
        #logging.debug("Docker logs command:%s" % docker_logs_cmd)

        docker_run_cmd = ("docker run -i -t {app_container}").format(app_container=app_cont_name)

        logged_status = []
        app_url = "1.2.3.4"
        deployment_done = False
        while not deployment_done:
            log_ = subprocess.Popen(docker_run_cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True).communicate()[0]

            log_lines = subprocess.check_output(docker_run_cmd, shell=True)
            log_lines = log_lines.split("\n")
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

    def deploy(self, deploy_type, deploy_name):
        logging.debug("Google deployer called for app %s" %
                      self.task_def.app_data['app_name'])
        app_obj = app.App(self.task_def.app_data)
        app_obj.update_app_status("status::DEPLOYING")
        app_ip_addr = self._deploy_app_container(app_obj)
        app_obj.update_app_status("status::DEPLOYMENT_COMPLETE")
        app_obj.update_app_ip(app_ip_addr)