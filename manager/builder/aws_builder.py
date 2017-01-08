'''
Created on Jan 5, 2017

@author: devdatta
'''
import logging
import os

from docker import Client
from common import app
from common import service
from common import utils
from common import docker_lib

from manager.service_handler.mysql import aws_handler as awsh

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
        logging.debug("Container name that will be used in building:%s" % cont_name)

        self.docker_handler.build_container_image(cont_name,
                                                  "Dockerfile.deploy")

        os.chdir(cwd)

    def build(self, build_type, build_name):
        if build_type == 'service':
            logging.debug("AWS builder called for service")

            for serv in self.task_def.service_data:
                serv_handler = self.services[serv['service']['type']]
                utils.update_status(self.service_obj.get_status_file_location(),
                                    "BUILDING_ARTIFACTS_FOR_PROVISIONING_SERVICE_INSTANCE")
                # Invoke public interface
                serv_handler.build_instance_artifacts()
        elif build_type == 'app':
            logging.debug("Local builder called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status("BUILDING")
            self._build_app_container(app_obj)