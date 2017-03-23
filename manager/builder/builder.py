'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com> October 26, 2016
'''

from common import task_definition as td
import local_builder as lb
import google_builder as gb
import aws_builder as ab
from common import constants

from common import fm_logger

fmlogging = fm_logger.Logging()

import logging

class Builder(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.cloud = task_def.cloud_data['type']

    def build(self, build_type, build_name):
        fmlogging.debug("Executing build step")
        if self.cloud == constants.LOCAL_DOCKER:
            lb.LocalBuilder(self.task_def).build(build_type, build_name)
        elif self.cloud == constants.GOOGLE:
            gb.GoogleBuilder(self.task_def).build(build_type, build_name)
        elif self.cloud == constants.AWS:
            ab.AWSBuilder(self.task_def).build(build_type, build_name)
        else:
            print("Cloud %s not supported" % self.cloud)

    def build_for_delete(self, info):
        fmlogging.debug("Executing build step for delete")
        if self.cloud == constants.LOCAL_DOCKER:
            lb.LocalBuilder(self.task_def).build_for_delete(info)
        elif self.cloud == constants.GOOGLE:
            gb.GoogleBuilder(self.task_def).build_for_delete(info)
        elif self.cloud == constants.AWS:
            ab.AWSBuilder(self.task_def).build_for_delete(info)
        else:
            print("Cloud %s not supported" % self.cloud)

    def build_for_logs(self, info):
        fmlogging.debug("Executing build step for building container to obtain app logs")
        if self.cloud == constants.LOCAL_DOCKER:
            lb.LocalBuilder(self.task_def).build_for_logs(info)
        elif self.cloud == constants.GOOGLE:
            gb.GoogleBuilder(self.task_def).build_for_logs(info)
        elif self.cloud == constants.AWS:
            ab.AWSBuilder(self.task_def).build_for_logs(info)
        else:
            print("Cloud %s not supported" % self.cloud)
