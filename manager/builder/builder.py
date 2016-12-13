'''
Created on Oct 26, 2016

@author: devdatta
'''

from common import task_definition as td
import local_builder as lb

class Builder(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.cloud = task_def.cloud_data['cloud']
        
    def build(self, build_type, build_name):
        if self.cloud == 'local' or self.cloud == 'aws' or self.cloud == 'google':
            lb.LocalBuilder(self.task_def).build(build_type, build_name)
        else:
            print("Cloud %s not supported" % self.cloud)
