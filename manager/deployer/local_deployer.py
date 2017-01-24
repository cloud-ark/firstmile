'''
Created on Oct 26, 2016

@author: devdatta
'''
import logging
import subprocess

from docker import Client
from common import app
from common import service
from common import utils
from common import constants
from common import docker_lib
from manager.service_handler.mysql import local_handler as lh

class LocalDeployer(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')
        
        self.services = {}

        if task_def.app_data:
            self.app_port = task_def.app_data['app_port']

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
        
        # get host port
        # app_port_list = cont_data['NetworkSettings']['Ports']
        # port_list = app_port_list["5000/tcp"]
        # app_host_port = port_list[0]["HostPort"]
        
        app_url = ("{app_ip_addr}:{app_port}").format(app_ip_addr=app_ip_addr,
                                                      app_port=self.app_port)
        
        logging.debug("App URL: %s" % app_url)
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
                    return addr
        except Exception as e:
            logging.error(e)

        return addr

    def _deploy_app_container(self, app_obj):
        app_cont_name = app_obj.get_cont_name()

        run_cmd = ("docker run -i -d --publish-all=true {cont_name}").format(cont_name=app_cont_name)

        try:
            cont_id = subprocess.Popen(run_cmd, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, shell=True).communicate()[0]

            app_ip_addr = self._parse_app_ip(cont_id)

        except Exception as e:
            logging.error(e)

        app_url = ("{app_ip_addr}:{app_port}").format(app_ip_addr=app_ip_addr,
                                                      app_port=self.app_port)

        logging.debug("App URL: %s" % app_url)
        return app_url

    def deploy_for_delete(self, info):
        logging.debug("Local deployer for called to delete app:%s" % info['app_name'])

        app_name = info['app_name']
        app_version = info['app_version']
        app_cont_name = app_name + "-" + app_version
        if app_name:
            self.docker_handler.stop_container(app_cont_name, "Stopping app cont " + app_cont_name)
            self.docker_handler.remove_container(app_cont_name, "Removing app cont " + app_cont_name)
            self.docker_handler.remove_container_image(app_cont_name, "Removing app cont img" + app_cont_name)
            utils.remove_app(info['dep_id'], app_name, app_version)

        service_name = info['service_name']
        service_version = info['service_version']
        service_cont_name = service_name + "-" + service_version
        if service_name:
            self.docker_handler.stop_container(app_cont_name,
                                               "Stopping service cont " + service_cont_name)
            self.docker_handler.remove_container(app_cont_name,
                                                 "Removing service cont " + service_cont_name)
            self.docker_handler.remove_container_image(app_cont_name,
                                                       "Removing service cont img " + service_cont_name)

    def deploy(self, deploy_type, deploy_name):
        if deploy_type == 'service':
            logging.debug("Local deployer called for service %s" % deploy_name)
            utils.update_status(self.service_obj.get_status_file_location(), "DEPLOYING_SERVICE_INSTANCE")
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
            logging.debug("Local deployer called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status(constants.DEPLOYING_APP)
            ip_addr = self._deploy_app_container(app_obj)
            app_obj.update_app_status(constants.APP_DEPLOYMENT_COMPLETE)
            app_obj.update_app_ip(ip_addr)
        return ip_addr