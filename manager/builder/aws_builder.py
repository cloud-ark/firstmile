'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com>, January 5, 2017
'''

import logging
import os
import subprocess

from common import app
from common import service
from common import utils
from common import docker_lib
from common import constants
from common import fm_logger

from manager.service_handler.mysql import aws_handler as awsh

fmlogging = fm_logger.Logging()

class AWSBuilder(object):

    def __init__(self, task_def):
        self.task_def = task_def
        if task_def.app_data:
            self.app_dir = task_def.app_data['app_location']
            self.app_name = task_def.app_data['app_name']
            self.app_version = task_def.app_data['app_version']

        self.services = {}

        if task_def.service_data:
            self.service_obj = service.Service(task_def.service_data[0])
            if self.service_obj.get_service_type() == 'mysql':
                self.services['mysql'] = awsh.MySQLServiceHandler(self.task_def)
                
        self.docker_handler = docker_lib.DockerLib()

    def _build_app_container(self, app_obj):
        cwd = os.getcwd()
        app_dir = self.task_def.app_data['app_location']
        app_name = self.task_def.app_data['app_name']
        os.chdir(app_dir + "/" + app_name)

        cont_name = app_obj.get_cont_name()
        fmlogging.debug("Container name that will be used in building:%s" % cont_name)

        self.docker_handler.build_container_image(cont_name,
                                                  "Dockerfile.deploy")

        os.chdir(cwd)

    def build_for_logs(self, info):
        fmlogging.debug("AWS builder called for getting app logs of app:%s" % info['app_name'])

        app_name = info['app_name']
        app_version = info['app_version']
        app_dir = (constants.APP_STORE_PATH + "/{app_name}/{app_version}/{app_name}").format(app_name=app_name,
                                                                                             app_version=app_version)
        cwd = os.getcwd()
        os.chdir(app_dir)
        output = ''

        try:
            cont_name = app_name + "-" + app_version
            cmd = ("docker build -t {app_name}-getec2-ip -f Dockerfile.get-instance-ip .").format(app_name=cont_name)
            output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True).communicate()[0]
        except Exception as e:
            self.logger.error(e)

        # Parse the PublicIPAddress of the EC2 instance
        env_name = utils.read_environment_name(app_dir)

        public_ip = ""
        public_ip_of_ec2_instance = ''
        for line in output.split("\n"):
            if line.find("PublicIp") >= 0:
                prts = line.split(":")
                public_ip = prts[1].rstrip().lstrip().replace(",","").replace("\"","")
            if line.find("Value") >= 0:
                prts = line.split(":")
                is_env_name = prts[1].rstrip().lstrip().replace(",","").replace("\"","")
            if line.find("Key") >= 0:
                prts = line.split(":")
                if prts and len(prts) >= 3:
                    env_key = prts[1].rstrip().lstrip().replace(",","").replace("\"","")
                    env_key1 = prts[2].rstrip().lstrip().replace(",","").replace("\"","")
                    if env_key.find("elasticbeanstalk") >= 0 and env_key1.find("environment-name") >= 0:
                        if is_env_name == env_name:
                            fmlogging.debug("Public IP of EC2 instance:%s" % public_ip)
                            public_ip_of_ec2_instance = public_ip
                            break

        # Plug the public_ip in Dockerfile.retrieve-logs
        pem_file = env_name + ".pem"
        fp = open("Dockerfile.retrieve-logs", "a")
        ssh_cmd = (" && ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "
                   "-i ~/.ssh/{pem_file} ec2-user@{public_ip} 'bash -s' < {ret_log_sh} \ \n "
                   ).format(pem_file=pem_file, public_ip=public_ip_of_ec2_instance, ret_log_sh=constants.RETRIEVE_LOG_PATH)

        runtime_log = app_version + constants.RUNTIME_LOG
        scp_cmd = (" && scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "
                   "-i ~/.ssh/{pem_file} ec2-user@{public_ip}:/home/ec2-user/uwsgi.log {runtime_log} \n "
                   ).format(pem_file=pem_file, public_ip=public_ip_of_ec2_instance, runtime_log=runtime_log)

        fp.write(ssh_cmd)
        fp.write(scp_cmd)
        fp.flush()
        fp.close()

        log_cont_name = ("{app_name}-retrieve-logs").format(app_name=cont_name)
        cmd = ("docker build -t {log_cont_name} -f Dockerfile.retrieve-logs .").format(log_cont_name=log_cont_name)
        os.system(cmd)

        os.chdir(cwd)

    def build_for_delete(self, info):
        fmlogging.debug("AWS builder called for delete of app:%s" % info['app_name'])

        app_name = info['app_name']
        app_version = info['app_version']
        app_dir = (constants.APP_STORE_PATH + "/{app_name}/{app_version}/{app_name}").format(app_name=app_name,
                                                                                             app_version=app_version)
        cwd = os.getcwd()
        os.chdir(app_dir)
        self.docker_handler.build_container_image(app_name + "-delete", "Dockerfile.delete")

        if os.path.exists("./Dockerfile.status"):
            self.docker_handler.build_container_image(app_name + "-status", "Dockerfile.status")

        os.chdir(cwd)
        self.docker_handler.remove_container_image(app_name + "-delete", "done deleting the app")

    def build(self, build_type, build_name):
        if build_type == 'service':
            fmlogging.debug("AWS builder called for service")

            for serv in self.task_def.service_data:
                serv_handler = self.services[serv['service']['type']]
                utils.update_status(self.service_obj.get_status_file_location(),
                                    "BUILDING_ARTIFACTS_FOR_PROVISIONING_SERVICE_INSTANCE")
                # Invoke public interface
                serv_handler.build_instance_artifacts()
        elif build_type == 'app':
            fmlogging.debug("Local builder called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status("BUILDING")
            self._build_app_container(app_obj)