'''
Created on Oct 26, 2016

@author: devdatta
'''

from common import task_definition as td

class Builder(object):
    
    def __init__(self, task_def):
        self.task = task_def
        self.app_name = task_def.task_definition['app_name']
        self.app_location = task_def.task_definition['app_location']
        
    def build(self):
        print("Builder called for app %s" % self.app_name)
