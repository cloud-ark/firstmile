'''
Created on Oct 26, 2016

@author: devdatta
'''
from common import task_definition as td
import local_generator as lg
import aws_generator as ag
import google_generator as gg

class Generator(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.cloud = task_def.cloud_data['type']
        
    def generate(self, generate_type, service_ip_addresses_dict, services):
        if self.cloud == 'local':
            lg.LocalGenerator(self.task_def).generate(generate_type, service_ip_addresses_dict)
        elif self.cloud == 'aws':
            ag.AWSGenerator(self.task_def).generate(generate_type, service_ip_addresses_dict, services)
        elif self.cloud == 'google':
            gg.GoogleGenerator(self.task_def).generate(generate_type, service_ip_addresses_dict, services)
        else:
            print("Cloud %s not supported" % self.cloud)
