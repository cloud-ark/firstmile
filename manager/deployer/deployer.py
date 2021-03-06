import logging
from common import task_definition as td
from common import constants
from common import fm_logger

import local_deployer as ld
import aws_deployer as ad
import google_deployer as gd

fmlogging = fm_logger.Logging()

class Deployer(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.cloud = task_def.cloud_data['type']

    def deploy(self, deploy_type, deploy_name):
        result = ''
        if self.cloud == constants.LOCAL_DOCKER:
            result = ld.LocalDeployer(self.task_def).deploy(deploy_type, deploy_name)
        elif self.cloud == constants.AWS:
            result = ad.AWSDeployer(self.task_def).deploy(deploy_type, deploy_name)
        elif self.cloud == constants.GOOGLE:
            result = gd.GoogleDeployer(self.task_def).deploy(deploy_type, deploy_name)
        else:
            print("(Deployer) Cloud %s not supported" % self.cloud)

        if result:
            fmlogging.debug("Deployment result:%s" % result)
        return result

    def deploy_for_delete(self, info):
        result = ''
        if self.cloud == constants.LOCAL_DOCKER:
            result = ld.LocalDeployer(self.task_def).deploy_for_delete(info)
        elif self.cloud == constants.AWS:
            result = ad.AWSDeployer(self.task_def).deploy_for_delete(info)
        elif self.cloud == constants.GOOGLE:
            result = gd.GoogleDeployer(self.task_def).deploy_for_delete(info)
        else:
            print("(Deployer) Cloud %s not supported" % self.cloud)

        if result:
            fmlogging.debug("Deployment result:%s" % result)
        return result

    def get_logs(self, info):
        result = ''
        if self.cloud == constants.LOCAL_DOCKER:
            result = ld.LocalDeployer(self.task_def).get_logs(info)
        elif self.cloud == constants.AWS:
            result = ad.AWSDeployer(self.task_def).get_logs(info)
        elif self.cloud == constants.GOOGLE:
            result = gd.GoogleDeployer(self.task_def).get_logs(info)
        else:
            print("(Deployer) Cloud %s not supported" % self.cloud)

        if result:
            fmlogging.debug("Deployment result:%s" % result)
        return result

    def deploy_to_secure(self, info):
        result = ''
        if self.cloud == constants.LOCAL_DOCKER:
            result = ld.LocalDeployer(self.task_def).deploy_to_secure(info)
        elif self.cloud == constants.AWS:
            result = ad.AWSDeployer(self.task_def).deploy_to_secure(info)
        elif self.cloud == constants.GOOGLE:
            result = gd.GoogleDeployer(self.task_def).deploy_to_secure(info)
        else:
            print("(Deployer) Cloud %s not supported" % self.cloud)

        if result:
            fmlogging.debug("Deployment result:%s" % result)
        return result

