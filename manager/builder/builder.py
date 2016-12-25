'''
Created on Oct 26, 2016

@author: devdatta
'''

from common import task_definition as td
import local_builder as lb
import google_builder as gb

import logging

class Builder(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.cloud = task_def.cloud_data['type']
        
    def build(self, build_type, build_name):
        if self.cloud == 'local' or self.cloud == 'aws':
            lb.LocalBuilder(self.task_def).build(build_type, build_name)
        elif self.cloud == 'google':
            gb.GoogleBuilder(self.task_def).build(build_type, build_name)
        else:
            print("Cloud %s not supported" % self.cloud)
