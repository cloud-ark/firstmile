'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com>, October 26, 2016
'''

import logging
import subprocess

from docker import Client
from common import app
from common import service
from common import utils
from common import constants
from common import docker_lib
from common import fm_logger

from manager.service_handler.mysql import local_handler as lh

fmlogging = fm_logger.Logging()

class LocalDeployer(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')
        
        self.services = {}

        if task_def.app_data:
            self.app_port = task_def.app_data['app_port']
            self.app_dir = task_def.app_data['app_location']
            self.app_name = task_def.app_data['app_name']
            self.app_version = task_def.app_data['app_version']

        if task_def.service_data:
            self.service_obj = service.Service(task_def.service_data[0])
            if self.service_obj.get_service_type() == 'mysql':
                self.services['mysql'] = lh.MySQLServiceHandler(self.task_def)

        self.docker_handler = docker_lib.DockerLib()

    def _deploy_app_container_prev(self, app_obj):
        app_cont_name = app_obj.get_cont_name()
        self.docker_client.import_image(image=app_cont_name)
        port_list = []
        port_list.append(self.app_port)
        host_cfg = self.docker_client.create_host_config(publish_all_ports=True)
        app_cont = self.docker_client.create_container(app_cont_name, detach=True,
                                                       ports=port_list, name=app_cont_name,
                                                       host_config=host_cfg)
        self.docker_client.start(app_cont)
        
        cont_data = self.docker_client.inspect_container(app_cont)
        
        app_ip_addr = cont_data['NetworkSettings']['IPAddress']
        localhost = 'localhost'

        # get host port
        app_port_list = cont_data['NetworkSettings']['Ports']
        port_list = app_port_list[self.app_port + "/tcp"]
        app_host_port = port_list[0]["HostPort"]
        
        app_url = ("{app_ip_addr}:{app_port}").format(app_ip_addr=localhost,
                                                      app_port=app_host_port)
        
        fmlogging.debug("App URL: %s" % app_url)
        return app_url

    def _parse_app_ip(self, cont_id):
        inspect_cmd = ("docker inspect {cont_id}").format(cont_id=cont_id)

        addr = ''
        try:
            out = subprocess.Popen(inspect_cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True).communicate()[0]
            all_lines = out.split("\n")
            for line in all_lines:
                if line.find("IPAddress") >= 0:
                    parts = line.split(":")
                    addr = parts[1].replace('"',"").replace(',','')
                    addr = addr.lstrip().rstrip()
                    if addr and addr != 'null':
                        break
        except Exception as e:
            fmlogging.error(e)

        return addr

    def _parse_app_port(self, cont_id):
        inspect_cmd = ("docker inspect {cont_id}").format(cont_id=cont_id)

        port = ''
        try:
            out = subprocess.Popen(inspect_cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True).communicate()[0]
            all_lines = out.split("\n")
            for line in all_lines:
                if line.find("HostPort") >= 0:
                    parts = line.split(":")
                    port = parts[1].replace('"',"").rstrip().lstrip()
                    if port and port != 'null':
                        break
        except Exception as e:
            fmlogging.error(e)

        return port

    def _deploy_app_container(self, app_obj):
        app_cont_name = app_obj.get_cont_name()

        run_cmd = ("docker run -i -d --publish-all=true {cont_name}").format(cont_name=app_cont_name)

        try:
            cont_id = subprocess.Popen(run_cmd, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, shell=True).communicate()[0]

            # Save cont_id as it is needed for obtaining logs
            fp = open("container_id.txt", "w")
            fp.write(cont_id)
            fp.flush()
            fp.close()

            app_ip_addr = 'localhost'
            app_port = self._parse_app_port(cont_id)

        except Exception as e:
            fmlogging.error(e)

        app_url = ("{app_ip_addr}:{app_port}").format(app_ip_addr=app_ip_addr,
                                                      app_port=app_port)

        fmlogging.debug("App URL: %s" % app_url)
        return app_url

    def _cleanup(self):
        # Remove app tar file
        app_name = self.app_name
        location = self.app_dir
        utils.delete_tar_file(location, app_name)

    def get_logs(self, info):
        fmlogging.debug("Local deployer called for getting app logs of app:%s" % info['app_name'])

    def deploy_for_delete(self, info):
        if info['app_name']:
            fmlogging.debug("Local deployer for called to delete app:%s" % info['app_name'])

            app_name = info['app_name']
            app_version = info['app_version']
            app_cont_name = app_name + "-" + app_version
            if app_name:
                self.docker_handler.stop_container(app_cont_name, "Stopping app cont " + app_cont_name)
                self.docker_handler.remove_container(app_cont_name, "Removing app cont " + app_cont_name)
                self.docker_handler.remove_container_image(app_cont_name, "Removing app cont img " + app_cont_name)
                utils.remove_artifact(info['dep_id'], constants.APP_STORE_PATH, "app_ids.txt", app_name, app_version)

                self.docker_handler.remove_container_image(constants.UBUNTU_IMAGE_NAME,
                                                           "Removing app cont img " + constants.UBUNTU_IMAGE_NAME)

        if info['service_name']:
            fmlogging.debug("Local deployer for called to delete service:%s" % info['service_name'])
            service_name = info['service_name']
            service_version = info['service_version']
            service_id = info['service_id']

            if service_name:
                parts = service_name.split("-")
                if parts[0] == 'mysql':
                    service_cont_name = lh.MySQLServiceHandler.get_instance_name(info)
                self.docker_handler.stop_container(service_cont_name,
                                                   "Stopping service cont " + service_cont_name)
                self.docker_handler.remove_container(service_cont_name,
                                                     "Removing service cont " + service_cont_name)
                self.docker_handler.remove_container_image(service_cont_name,
                                                           "Removing service cont img " + service_cont_name)

                utils.remove_artifact(service_id, constants.SERVICE_STORE_PATH,
                                      "service_ids.txt", service_name, service_version)

                self.docker_handler.remove_container_image(constants.MYSQL_IMAGE_NAME,
                                                           "Removing app cont img " + constants.MYSQL_IMAGE_NAME)

    def deploy(self, deploy_type, deploy_name):
        if deploy_type == 'service':
            fmlogging.debug("Local deployer called for service %s" % deploy_name)
            utils.update_status(self.service_obj.get_status_file_location(), constants.DEPLOYING_SERVICE_INSTANCE)
            serv_handler = self.services[deploy_name]
            utils.update_status(self.service_obj.get_status_file_location(),
                                constants.DEPLOYING_SERVICE_INSTANCE)
            # Invoke public interface
            service_ip = serv_handler.provision_and_setup()
            utils.update_status(self.service_obj.get_status_file_location(),
                                constants.SERVICE_INSTANCE_DEPLOYMENT_COMPLETE)
            utils.save_service_instance_ip(self.service_obj.get_status_file_location(), service_ip)

            # TODO(devkulkarni): Add support for returning multiple service IPs
            return service_ip
        elif deploy_type == 'app':
            fmlogging.debug("Local deployer called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status(constants.DEPLOYING_APP)
            ip_addr = self._deploy_app_container(app_obj)
            if ip_addr:
                app_obj.update_app_status(constants.APP_DEPLOYMENT_COMPLETE)
            else:
                app_obj.update_app_status(constants.DEPLOYMENT_ERROR)
            app_obj.update_app_ip(ip_addr)
            self._cleanup()
        return ip_addr