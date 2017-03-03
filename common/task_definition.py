'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com> October 26 2016
'''

class TaskDefinition(object):
    
    def __init__(self, app_data, cloud_data, service_data):
        self.app_data = app_data
        self.cloud_data = cloud_data
        self.service_data = service_data