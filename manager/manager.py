import logging
import threading
import time
from common import task_definition as td
from builder import builder as bld
from generator import generator as gen
from deployer import deployer as dep

from common import app
from common import constants
from common import service
from common import utils
from common import fm_logger

fmlogging = fm_logger.Logging()

class Manager(threading.Thread):

    def __init__(self, name='', task_def='', action='', info=''):
        threading.Thread.__init__(self)
        self.name = name
        self.task_def = task_def
        self.action = action
        self.info = info
        
    def error_update(self):
        if self.task_def.app_data:
            app_name = self.task_def.app_data['app_name']
            location = self.task_def.app_data['app_location']
            #utils.delete_tar_file(location, app_name)
            #utils.delete_app_folder(location, app_name)
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status(constants.DEPLOYMENT_ERROR)

    def run(self):
        fmlogging.debug("Starting build/deploy for %s" % self.name)

        if self.action == "delete":
            fmlogging.debug("Manager -- delete")
            gen.Generator(self.task_def).generate_for_delete(self.info)
            bld.Builder(self.task_def).build_for_delete(self.info)
            dep.Deployer(self.task_def).deploy_for_delete(self.info)
        elif self.action == "secure":
            fmlogging.debug("Manager -- secure")
            gen.Generator(self.task_def).generate_to_secure(self.info)
            bld.Builder(self.task_def).build_to_secure(self.info)
            dep.Deployer(self.task_def).deploy_to_secure(self.info)
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
                service_kind = service_obj.get_service_type()
                utils.update_status(service_obj.get_status_file_location(), "name::" + service_name)
                utils.update_status(service_obj.get_status_file_location(), "cloud::" + cloud)

                try:
                    gen.Generator(self.task_def).generate('service', service_ip_addresses, services)
                    bld.Builder(self.task_def).build(build_type='service', build_name=service_name)
                    serv_ip_addr = dep.Deployer(self.task_def).deploy(deploy_type='service',
                                                                      deploy_name=service_kind)
                    fmlogging.debug("IP Address of the service:%s" % serv_ip_addr)
                    service_ip_addresses[service_kind] = serv_ip_addr
                except Exception as e:
                    fmlogging.error(e)
                    raise e

            # Step 2:
            # - Generate, build, deploy app
            if self.task_def.app_data:
                # Allow time for service container to be deployed and started
                time.sleep(5)
                try:
                    gen.Generator(self.task_def).generate('app', service_ip_addresses, services)
                    bld.Builder(self.task_def).build(build_type='app', build_name=self.task_def.app_data['app_name'])
                    result = dep.Deployer(self.task_def).deploy(deploy_type='app',
                                                                deploy_name=self.task_def.app_data['app_name']
                                                                )
                    fmlogging.debug("Result:%s" % result)
                except Exception as e:
                    fmlogging.error(e)
                    raise e

    def get_logs(self, info):
        fmlogging.debug("Manager -- logs")
        gen.Generator(self.task_def).generate_for_logs(info)
        bld.Builder(self.task_def).build_for_logs(info)
        dep.Deployer(self.task_def).get_logs(info)
