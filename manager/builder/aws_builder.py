'''
Created on Jan 5, 2017

@author: devdatta
'''
import logging
import os
import subprocess

from docker import Client
from common import app
from common import service
from common import utils

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
                
                
    def build(self, build_type, build_name):
        if build_type == 'service':
            logging.debug("AWS builder called for service")

            for serv in self.task_def.service_data:
                serv_handler = self.services[serv['service']['type']]
                utils.update_status(self.service_obj.get_status_file_location(),
                                    "BUILDING_ARTIFACTS_FOR_PROVISIONING_SERVICE_INSTANCE")
                # Invoke public interface
                serv_handler.build_instance_artifacts()

