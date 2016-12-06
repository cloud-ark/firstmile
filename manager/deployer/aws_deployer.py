'''
Created on Dec 6, 2016

@author: devdatta
'''
import logging
import os
import subprocess

from docker import Client
from common import app

class AWSDeployer(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')
        
    def _process_logs(self, cont_id, app_obj):
        is_env_ok = False
        docker_logs_cmd = ("docker logs {cont_id}").format(cont_id=cont_id)
        logging.debug("Fetching Docker logs")
        logging.debug("Docker logs command:%s" % docker_logs_cmd)
        logged_status = []
        cname = "1.2.3.4"
        while not is_env_ok:
            log_lines = subprocess.check_output(docker_logs_cmd, shell=True)
            log_lines = log_lines.split("\n")
            for line in log_lines:
                if line.find("CNAME:") >= 0:
                    stat = line.split(":")
                    cname = stat[1].rstrip().lstrip()
                if line.find("INFO:") >= 0:
                    stat = line.split(":")
                    status = stat[1]
                    if status not in logged_status:
                        logged_status.append(status)
                        trimmed_status = status.replace("named"," ")
                        app_obj.update_app_status("status::" + trimmed_status)
                    if status.lower().find("successfully launched environment") > 0:
                        is_env_ok = True
        return cname
        
    def _deploy_app_container(self, app_obj):
        app_cont_name = app_obj.get_cont_name()
        
        logging.debug("Deploying app container:%s" % app_cont_name)

        #self.docker_client.import_image(image=app_cont_name)
        #host_cfg = self.docker_client.create_host_config()
        #app_cont = self.docker_client.create_container(app_cont_name, detach=True,
        #                                               name=app_cont_name,
        #                                               host_config=host_cfg)
        #self.docker_client.start(app_cont)
        #response = self.docker_client.logs(app_cont)
        
        docker_run_cmd = ("docker run -i -t -d {app_container}").format(app_container=app_cont_name)
        cont_id = subprocess.check_output(docker_run_cmd, shell=True)
        logging.debug("Running container id:%s" % cont_id)
        
        cname = self._process_logs(cont_id, app_obj)
        return cname
        
        #logging.debug("Logs from running %s container" % app_cont)
        #logging.debug(response)
        
    def deploy(self, deploy_type, deploy_name):
        logging.debug("Local deployer called for app %s" %
                      self.task_def.app_data['app_name'])
        app_obj = app.App(self.task_def.app_data)
        app_obj.update_app_status("status::DEPLOYING")
        app_ip_addr = self._deploy_app_container(app_obj)
        ip_addr = app_ip_addr
        app_obj.update_app_status("status::DEPLOYMENT_COMPLETE")
        app_obj.update_app_ip(ip_addr)
