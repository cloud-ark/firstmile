'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com>, October 26, 2016
'''

import json
import os
import re
import subprocess

from io import BytesIO
from docker import Client
from common import app
from common import constants
from common import docker_lib
from common import fm_logger

fmlogging = fm_logger.Logging()

class LocalBuilder(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')
        self.docker_handler = docker_lib.DockerLib()
        
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

        fmlogging.debug(parsed_lines)

    def _build_app_container(self, app_obj):
        app_dir = self.task_def.app_data['app_location']
        app_name = self.task_def.app_data['app_name']

        df_dir = app_dir + "/" + app_name

        cont_name = app_obj.get_cont_name()
        fmlogging.debug("Container name that will be used in building:%s" % cont_name)
        
        # Following is not working, so continuing to use 'docker build'
        # self._do_docker_build(cont_name)

        self.docker_handler.build_container_image(cont_name, df_dir + "/Dockerfile", df_context=df_dir)

    def build_for_delete(self, info):
        if info['app_name']:
            fmlogging.debug("Local builder called for delete of app:%s" % info['app_name'])
        if info['service_name']:
            fmlogging.debug("Local builder called for delete of service:%s" % info['service_name'])

    def build_for_logs(self, info):
        fmlogging.debug("Local builder called for getting app logs of app:%s" % info['app_name'])

        app_name = info['app_name']
        app_version = info['app_version']
        app_dir = (constants.APP_STORE_PATH + "/{app_name}/{app_version}/").format(app_name=app_name,
                                                                                   app_version=app_version)

        if os.path.exists(app_dir + "/container_id.txt"):
            fp = open(app_dir + "/container_id.txt")
            all_lines = fp.readlines()
            # Should be only one line
            cont_id = all_lines[0].rstrip().lstrip()
            logs_cmd = ("docker logs {cont_id}").format(cont_id=cont_id)

            fmlogging.debug("Logs cmd:%s" % logs_cmd)
            logs_file = ("{app_dir}{app_version}{runtime_log}").format(app_dir=app_dir,
                                                                       app_version=app_version,
                                                                       runtime_log=constants.RUNTIME_LOG)
            fp1 = open(logs_file, "w")

            ppe = subprocess.Popen(logs_cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True).communicate()
            out = ppe[0]
            err = ppe[1]
            fp1.write(out)
            fp1.write("\n----\n")
            fp1.write(err)
            fp1.flush()
            fp1.close()
            fp.close()

    def build_to_secure(self, info):
        fmlogging.debug("Local builder called for securing service:%s" % info['service_name'])

    def build(self, build_type, build_name):
        if build_type == 'service':
            fmlogging.debug("Local builder called for service %s" % build_name)
            self._build_service_container()
        elif build_type == 'app':
            fmlogging.debug("Local builder called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status("BUILDING")
            self._build_app_container(app_obj)
        return 0
