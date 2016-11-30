'''
Created on Oct 26, 2016

@author: devdatta
'''
import threading
import time
from common import task_definition as td
from builder import builder as bld
from generator import generator as gen
from deployer import deployer as dep

from common import app

class Manager(threading.Thread):
    
    def __init__(self, name, task_def):
        threading.Thread.__init__(self)
        self.name = name
        self.task_def = task_def
        
    def run(self):
        print "Starting build/deploy for " + self.name
        app_obj = app.App(self.task_def.app_data)
        app_cont_name = app_obj.get_cont_name()
        
        # Two-step protocol
        # Step 1: For each service build and deploy. Collect the IP address of deployed service
        # Step 2: Generate, build, deploy application. Pass the IP addresses of the services
        
        app_obj.update_app_status("Starting build")

        # Step 1:
        service_ip_addresses = {}
        services = self.task_def.service_data
        for serv in services:
            service_name = serv['service_name']
            service_type = serv['service_type']
            service_details = serv['service_details']

            bld.Builder(self.task_def).build(build_type='service', build_name=service_name)
            serv_ip_addr = dep.Deployer(self.task_def).deploy(deploy_type='service', 
                                                              deploy_name=service_name)
            service_ip_addresses[service_name] = serv_ip_addr

            # Allow time for service container to be deployed and started
            time.sleep(10)
        
        # Step 2:
        # - Generate, build, deploy app
        gen.Generator(self.task_def).generate(service_ip_addresses)
        bld.Builder(self.task_def).build(build_type='app', build_name=self.task_def.app_data['app_name'])
        result = dep.Deployer(self.task_def).deploy(deploy_type='app', deploy_name=self.task_def.app_data['app_name'])
        print("Manager, result:%s" % result)
        

        
        

        
    
        

