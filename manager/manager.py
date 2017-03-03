'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com> October 26 2016
'''

import logging
import threading
import time
from common import task_definition as td
from builder import builder as bld
from generator import generator as gen
from deployer import deployer as dep

from common import app
from common import service
from common import utils

class Manager(threading.Thread):
    
    def __init__(self, name='', task_def='', delete_action=False, delete_info=''):
        threading.Thread.__init__(self)
        self.name = name
        self.task_def = task_def
        self.delete_action = delete_action
        self.delete_info = delete_info
        
    def run(self):
        logging.debug("Starting build/deploy for %s" % self.name)

        if self.delete_action:
            logging.debug("Manager -- delete")
            gen.Generator(self.task_def).generate_for_delete(self.delete_info)
            bld.Builder(self.task_def).build_for_delete(self.delete_info)
            dep.Deployer(self.task_def).deploy_for_delete(self.delete_info)
        else:
            if self.task_def.app_data:
                app_obj = app.App(self.task_def.app_data)
                app_obj.update_app_status("name::" + self.name)
                app_obj.update_app_status("cloud::" + self.task_def.cloud_data['type'])
                app_cont_name = app_obj.get_cont_name()

            # Two-step protocol
            # Step 1: For each service build and deploy. Collect the IP address of deployed service
            # Step 2: Generate, build, deploy application. Pass the IP addresses of the services

            # Step 1:
            service_ip_addresses = {}
            services = self.task_def.service_data

            cloud = self.task_def.cloud_data['type']
            for serv in services:
                service_obj = service.Service(serv)
                service_name = service_obj.get_service_name()
                utils.update_status(service_obj.get_status_file_location(), "name::" + service_name)
                utils.update_status(service_obj.get_status_file_location(), "cloud::" + cloud)

                gen.Generator(self.task_def).generate('service', service_ip_addresses, services)
                bld.Builder(self.task_def).build(build_type='service', build_name=service_name)
                serv_ip_addr = dep.Deployer(self.task_def).deploy(deploy_type='service',
                                                                  deploy_name=service_name)
                logging.debug("IP Address of the service:%s" % serv_ip_addr)
                service_ip_addresses[service_name] = serv_ip_addr

            # Step 2:
            # - Generate, build, deploy app
            if self.task_def.app_data:
                # Allow time for service container to be deployed and started
                time.sleep(5)
                gen.Generator(self.task_def).generate('app', service_ip_addresses, services)
                bld.Builder(self.task_def).build(build_type='app', build_name=self.task_def.app_data['app_name'])
                result = dep.Deployer(self.task_def).deploy(deploy_type='app',
                                                            deploy_name=self.task_def.app_data['app_name']
                                                            )
                logging.debug("Result:%s" % result)

    def get_logs(self, info):
        logging.debug("Manager -- logs")
        gen.Generator(self.task_def).generate_for_logs(info)
        bld.Builder(self.task_def).build_for_logs(info)
        dep.Deployer(self.task_def).get_logs(info)