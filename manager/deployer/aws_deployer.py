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
from common import constants

TMP_LOG_FILE = "/tmp/lme-aws-deploy-output.txt"

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

    def _process_logs(self, cont_id, app_cont_name, app_obj, tmp_log_file_name, services_defined=False):

        logging.debug("Fetching logs from AWS deployer container")
        logged_status = []
        if services_defined:
            cont_id = self._parse_container_id(app_cont_name)
        docker_logs_cmd = ("docker logs {cont_id}").format(cont_id=cont_id)
        logging.debug("Docker logs command:%s" % docker_logs_cmd)
        cname = "1.2.3.4"
        #else:
        #    fp = open(tmp_log_file_name, "r")

        is_env_ok = False
        logging.debug("Parsing statuses from AWS")
        while not is_env_ok:
            #if not services_defined:
            #    log_lines = fp.readlines()
            #else:
            log_lines = subprocess.check_output(docker_logs_cmd, shell=True)
            log_lines = log_lines.split("\n")
            #logging.debug("Log lines:%s" % log_lines)
            for line in log_lines:
                line = line.rstrip().lstrip()
                if line.find("CNAME:") >= 0:
                    stat = line.split(":")
                    cname = stat[1].rstrip().lstrip()
                    #logging.debug("CNAME:%s" % cname)
                if line.find("ERROR:") >= 0:
                    stat = line.split(":")
                    error = stat[1].rstrip().lstrip()
                    if error not in logged_status:
                        logged_status.append(error)
                        app_obj.update_app_status(error)
                if line.find("INFO:") >= 0:
                    stat = line.split(":")
                    status = stat[1]
                    if status not in logged_status:
                        logged_status.append(status)
                        #trimmed_status = status.replace("named"," ")
                        a = line.find("INFO:")
                        line = line[a+5:]
                        app_obj.update_app_status(line)
                    if status.lower().find("successfully launched environment") >= 0:
                        is_env_ok = True
            time.sleep(1)

        #if not services_defined:
        #    os.remove(tmp_log_file_name)

        return cname
        
    def _deploy_app_container(self, app_obj):
        app_cont_name = app_obj.get_cont_name()
        tmp_log_file_name = TMP_LOG_FILE+"-"+app_cont_name
        
        logging.debug("Deploying app container:%s" % app_cont_name)

        #self.docker_client.import_image(image=app_cont_name)
        #host_cfg = self.docker_client.create_host_config()
        #app_cont = self.docker_client.create_container(app_cont_name, detach=True,
        #                                               name=app_cont_name,
        #                                               host_config=host_cfg)
        #self.docker_client.start(app_cont)
        #response = self.docker_client.logs(app_cont)

        services_defined = False
        services = self.task_def.service_data
        cont_id = ''
        if services:
            logging.debug("Looks like app requires Amazon RDS instance. Spawning and providing setup credentials")
            # Provide RDS username and password
            services_defined = True
            try:
                docker_run_cmd = ("docker run -i -t {app_container}").format(app_container=app_cont_name)
                #docker_attach_cmd = ("docker attach {cont_id}").format(cont_id=cont_id)
                #logging.debug("docker attach cmd:%s" % docker_attach_cmd)
                # Allow the platform to get ready
                #logging.debug("Allowing AWS to do its thing. Waiting for 20 seconds before continuing..")
                #time.sleep(20)
                #child = pexpect.spawn(docker_attach_cmd)

                username_val = constants.DEFAULT_DB_USER
                password_val = constants.DEFAULT_DB_PASSWORD
                child = pexpect.spawn(docker_run_cmd)
                child.logfile = sys.stdout
                child.expect("Enter an RDS DB username*", timeout=120)
                child.sendline(username_val)
                child.expect("Enter an RDS DB master password*")
                child.sendline(password_val)
                child.expect("Retype password to confirm*")
                child.sendline(password_val)
                logging.debug("Done providing db creds to eb create command.")
                #child.close()
            except Exception as e:
                logging.error(e)
        else:
            docker_run_cmd = ("docker run -i -t -d {app_container}").format(app_container=app_cont_name)
            #os.system(docker_run_cmd)
            cont_id = subprocess.check_output(docker_run_cmd, shell=True)
            logging.debug("Running container id:%s" % cont_id)

        cname = self._process_logs(cont_id, app_cont_name, app_obj, tmp_log_file_name, services_defined)
        return cname
        
    def deploy(self, deploy_type, deploy_name):
        logging.debug("AWS deployer called for app %s" %
                      self.task_def.app_data['app_name'])
        app_obj = app.App(self.task_def.app_data)
        app_obj.update_app_status("DEPLOYING")
        app_ip_addr = self._deploy_app_container(app_obj)
        ip_addr = app_ip_addr
        app_obj.update_app_status("DEPLOYMENT_COMPLETE")
        app_obj.update_app_ip(ip_addr)
