'''
Created on Oct 26, 2016

@author: devdatta
'''
import json
import logging
import os
import subprocess
import re

from io import BytesIO
from docker import Client
from common import app

class LocalBuilder(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')
        
    def _build_service_container(self):
        pass
    
    def _do_docker_build(self, cont_name):
        dockerfile = open("Dockerfile", "r").read()
        f = BytesIO(dockerfile.encode('utf-8'))
        response = [line for line in self.docker_client.build(fileobj=f, rm=False,
                                                              tag=cont_name+":latest")]

        # Below code taken from https://github.com/docker/docker-py/issues/255
        # -----
        try:
            parsed_lines = [json.loads(e).get('stream', '') for e in response]
        except ValueError:
                # sometimes all the data is sent on a single line ????
                #
                # ValueError: Extra data: line 1 column 87 - line 1 column
                # 33268 (char 86 - 33267)
                line = response[0]
                # This ONLY works because every line is formatted as
                # {"stream": STRING}
                parsed_lines = [
                    json.loads(obj).get('stream', '') for obj in
                    re.findall('{\s*"stream"\s*:\s*"[^"]*"\s*}', line)
                ]
        # -----

        logging.debug(parsed_lines)

    def _build_app_container(self, app_obj):
        cwd = os.getcwd()
        app_dir = self.task_def.app_data['app_location']
        app_name = self.task_def.app_data['app_name']
        os.chdir(app_dir + "/" + app_name)

        cont_name = app_obj.get_cont_name()
        logging.debug("Container name that will be used in building:%s" % cont_name)
        
        # Following is not working, so continuing to use 'docker build'
        # self._do_docker_build(cont_name)

        build_cmd = ("docker build -t {name} . ").format(name=cont_name)
        logging.debug("Docker build command:%s" % build_cmd)

        result = subprocess.check_output(build_cmd, shell=True)
        logging.debug(result)

        os.chdir(cwd)

    def build(self, build_type, build_name):
        if build_type == 'service':
            logging.debug("Local builder called for service %s" % build_name)
            self._build_service_container()
        elif build_type == 'app':
            logging.debug("Local builder called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status("BUILDING")
            self._build_app_container(app_obj)
        return 0
