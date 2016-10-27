'''
Created on Oct 26, 2016

@author: devdatta
'''
class TaskDefinition(object):
    
    def __init__(self, app_data, cloud_data, service_data):
        self.app_data = app_data
        self.cloud_data = cloud_data
        self.service_data = service_data