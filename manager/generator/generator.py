'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com> October 26 2016
'''

from common import task_definition as td
from common import constants
import local_generator as lg
import aws_generator as ag
import google_generator as gg

class Generator(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.cloud = task_def.cloud_data['type']

    def generate(self, generate_type, service_ip_addresses_dict, services):
        if self.cloud == constants.LOCAL_DOCKER:
            lg.LocalGenerator(self.task_def).generate(generate_type, service_ip_addresses_dict)
        elif self.cloud == constants.AWS:
            ag.AWSGenerator(self.task_def).generate(generate_type, service_ip_addresses_dict, services)
        elif self.cloud == constants.GOOGLE:
            gg.GoogleGenerator(self.task_def).generate(generate_type, service_ip_addresses_dict, services)
        else:
            print("Cloud %s not supported" % self.cloud)

    def generate_for_delete(self, info):
        if self.cloud == constants.LOCAL_DOCKER:
            lg.LocalGenerator(self.task_def).generate_for_delete(info)
        elif self.cloud == constants.AWS:
            ag.AWSGenerator(self.task_def).generate_for_delete(info)
        elif self.cloud == constants.GOOGLE:
            gg.GoogleGenerator(self.task_def).generate_for_delete(info)
        else:
            print("Cloud %s not supported" % self.cloud)

    def generate_for_logs(self, info):
        if self.cloud == constants.LOCAL_DOCKER:
            lg.LocalGenerator(self.task_def).generate_for_logs(info)
        elif self.cloud == constants.AWS:
            ag.AWSGenerator(self.task_def).generate_for_logs(info)
        elif self.cloud == constants.GOOGLE:
            gg.GoogleGenerator(self.task_def).generate_for_logs(info)
        else:
            print("Cloud %s not supported" % self.cloud)
