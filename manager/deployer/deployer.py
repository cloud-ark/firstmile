'''
Created on Oct 26, 2016

@author: devdatta
'''
import logging
from common import task_definition as td
import local_deployer as ld

class Deployer(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.cloud = task_def.cloud_data['cloud']
        
    def deploy(self, deploy_type, deploy_name):
        if self.cloud == 'local':
            result = ld.LocalDeployer(self.task_def).deploy(deploy_type, deploy_name)
            logging.debug("Deployment result:%s" % result)
        else:
            print("Cloud %s not supported" % self.cloud)
        return result