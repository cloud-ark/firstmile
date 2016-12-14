'''
Created on Dec 6, 2016

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

class AWSDeployer(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')
        
    def _parse_container_id(self, app_cont_name):
        cont_grep_cmd = ("docker ps -a | grep {cont_name} | cut -d ' ' -f 1 ").format(cont_name=app_cont_name)
        logging.debug("Container grep command:%s" % cont_grep_cmd)
        cont_id = subprocess.check_output(cont_grep_cmd, shell=True)
        logging.debug("Container id:%s" % cont_id)
        return cont_id

    def _process_logs(self, cont_id, app_cont_name, app_obj):
        
        services = self.task_def.service_data

        if services:
            # Provide RDS username and password
            try:
                docker_run_cmd = ("docker run -i -t {app_container}").format(app_container=app_cont_name)
                #docker_attach_cmd = ("docker attach {cont_id}").format(cont_id=cont_id)
                #logging.debug("docker attach cmd:%s" % docker_attach_cmd)
                # Allow the platform to get ready
                logging.debug("Allowing AWS to do its thing. Waiting for 20 seconds before continuing..")
                time.sleep(20)
                #child = pexpect.spawn(docker_attach_cmd)
                child = pexpect.spawn(docker_run_cmd)
                child.logfile = sys.stdout
                child.expect("Enter an RDS DB username*", timeout=120)
                child.sendline("lmeroot")
                child.expect("Enter an RDS DB master password*")
                child.sendline("lmeroot123")
                child.expect("Retype password to confirm*")
                child.sendline("lmeroot123")
                #child.close()
            except Exception as e:
                logging.error(e)
        logging.debug("Done providing db creds to eb create command.")

        cont_id = self._parse_container_id(app_cont_name)

        docker_logs_cmd = ("docker logs {cont_id}").format(cont_id=cont_id)
        logging.debug("Fetching Docker logs")
        logging.debug("Docker logs command:%s" % docker_logs_cmd)
        logged_status = []
        cname = "1.2.3.4"
        is_env_ok = False
        while not is_env_ok:
            log_lines = subprocess.check_output(docker_logs_cmd, shell=True)
            #log_lines = child.logfile.read()
            log_lines = log_lines.split("\n")
            for line in log_lines:
                if line.find("CNAME:") >= 0:
                    stat = line.split(":")
                    cname = stat[1].rstrip().lstrip()
                if line.find("ERROR:") >= 0:
                    stat = line.split(":")
                    error = stat[1].rstrip().lstrip()
                    if error not in logged_status:
                        logged_status.append(error)
                        app_obj.update_app_status("status::" + error)
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
        
        services = self.task_def.service_data
        cont_id = ''
        if not services:
            docker_run_cmd = ("docker run -i -t -d {app_container}").format(app_container=app_cont_name)
            cont_id = subprocess.check_output(docker_run_cmd, shell=True)
            logging.debug("Running container id:%s" % cont_id)
        
        cname = self._process_logs(cont_id, app_cont_name, app_obj)
        return cname
        
        #logging.debug("Logs from running %s container" % app_cont)
        #logging.debug(response)
        
    def deploy(self, deploy_type, deploy_name):
        logging.debug("AWS deployer called for app %s" %
                      self.task_def.app_data['app_name'])
        app_obj = app.App(self.task_def.app_data)
        app_obj.update_app_status("status::DEPLOYING")
        app_ip_addr = self._deploy_app_container(app_obj)
        ip_addr = app_ip_addr
        app_obj.update_app_status("status::DEPLOYMENT_COMPLETE")
        app_obj.update_app_ip(ip_addr)
