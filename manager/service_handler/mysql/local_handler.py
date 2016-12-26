'''
Created on Dec 24, 2016

@author: devdatta
'''
import logging
import os
import stat
import subprocess
import time

from docker import Client

from common import docker_lib
from common import service
from common import utils

class MySQLServiceHandler(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')

        import pdb; pdb.set_trace()
        self.service_obj = service.Service(self.task_def.service_data[0])
        self.service_name = self.service_obj.get_service_name()
        self.mysql_db_name = 'testdb'
        self.mysql_user = 'testuser'
        self.mysql_password = 'testuserpass'
        self.mysql_root_password = 'rootuserpass'
        self.mysql_version = 'mysql:5.5'
        
        fp = open(self.service_obj.get_service_details_file_location(), "w")
        fp.write("MYSQL_DB_NAME::%s\n" % self.mysql_db_name)
        fp.write("MYSQL_DB_USER::%s\n" % self.mysql_user)
        fp.write("MYSQL_DB_USER_PASSWORD::%s\n" % self.mysql_password)
        fp.write("MYSQL_ROOT_USER_PASSWORD::%s\n" % self.mysql_root_password)
        fp.write("MYSQL_VERSION::%s\n" % self.mysql_version)
        fp.close()

    def _get_cont_name(self):
        if self.task_def.app_data:        
            app_name = self.task_def.app_data['app_name']
            app_loc = self.task_def.app_data['app_location']
            k = app_loc.rfind("/")
            app_loc = app_loc[k+1:]
            app_loc = app_loc.replace(":","-")
            cont_name = app_name + "-" + app_loc + "-mysql"
        else:
            serv_version = self.service_obj.get_service_version()
            cont_name = serv_version + "-mysql"
        return cont_name

    def _deploy_service_container(self):             
        logging.debug("Deploying mysql container")
        #db_name = service_details['db_name']            
        env = {"MYSQL_ROOT_PASSWORD": self.mysql_root_password,
               "MYSQL_DATABASE": self.mysql_db_name,
               "MYSQL_USER": self.mysql_user,
               "MYSQL_PASSWORD": self.mysql_password}
        cont_name = self._get_cont_name()
                    
        self.docker_client.import_image(image=self.mysql_version)
        serv_cont = self.docker_client.create_container(self.mysql_version,
                                                        detach=True,
                                                        environment=env,
                                                        name=cont_name)
        self.docker_client.start(serv_cont)

        cont_data = self.docker_client.inspect_container(serv_cont)
        service_ip_addr = cont_data['NetworkSettings']['IPAddress']
        logging.debug("MySQL Service IP Address:%s" % service_ip_addr)
        return service_ip_addr
    
    def _setup_service_container(self):
        logging.debug("Setting up service container")
        pass

    # Public interface
    def provision_and_setup(self, access_token):
        service_ip = self._deploy_service_container()
        self._setup_service_container()
        return service_ip
    
    def cleanup(self):
        pass