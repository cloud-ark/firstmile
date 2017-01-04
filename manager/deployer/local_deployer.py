'''
Created on Oct 26, 2016

@author: devdatta
'''
import logging

from docker import Client
from common import app
from common import service
from common import utils
from manager.service_handler.mysql import local_handler as lh

class LocalDeployer(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')
        
        self.services = {}

        if task_def.service_data:
            self.service_obj = service.Service(task_def.service_data[0])
            if self.service_obj.get_service_type() == 'mysql':
                self.services['mysql'] = lh.MySQLServiceHandler(self.task_def)
    
    def _deploy_app_container(self, app_obj):
        app_cont_name = app_obj.get_cont_name()
        self.docker_client.import_image(image=app_cont_name)
        port_list = []
        port_list.append(5000)
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
        
        app_url = ("{app_ip_addr}:{app_port}").format(app_ip_addr=app_ip_addr, app_port=5000)
        
        logging.debug("App URL: %s" % app_url)
        return app_url

    def deploy(self, deploy_type, deploy_name):
        if deploy_type == 'service':
            logging.debug("Local deployer called for service %s" % deploy_name)
            utils.update_status(self.service_obj.get_status_file_location(), "Deploying service container")

            serv_handler = self.services[deploy_name]
            # Invoke public interface
            service_ip = serv_handler.provision_and_setup()
            utils.update_status(self.service_obj.get_status_file_location(),
                                "Service container deployment complete")
            utils.update_ip(self.service_obj.get_status_file_location(), service_ip)

            # TODO(devkulkarni): Add support for returning multiple service IPs
            return service_ip
        elif deploy_type == 'app':
            logging.debug("Local deployer called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status("DEPLOYING")
            ip_addr = self._deploy_app_container(app_obj)
            app_obj.update_app_status("DEPLOYMENT_COMPLETE")
            app_obj.update_app_ip(ip_addr)
        return ip_addr