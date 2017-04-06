'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com>, December 18, 2016
'''

import logging
import os
import subprocess

from docker import Client
from common import app
from common import service
from common import constants
from common import docker_lib
from common import fm_logger

from manager.service_handler.mysql import google_handler as gh

fmlogging = fm_logger.Logging()

class GoogleBuilder(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        if task_def.app_data:
            self.app_dir = task_def.app_data['app_location']
            self.app_name = task_def.app_data['app_name']
            self.app_version = task_def.app_data['app_version']

        self.services = {}

        if task_def.service_data:
            self.service_obj = service.Service(task_def.service_data[0])
            if self.service_obj.get_service_type() == 'mysql':
                self.services['mysql'] = gh.MySQLServiceHandler(self.task_def)

        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')
        self.docker_handler = docker_lib.DockerLib()


    def _build_first_time_container(self, app_obj):
        df_first_time_loc = self.app_dir[:self.app_dir.rfind("/")]
        
        try:
            gae_app_created = os.path.isfile(df_first_time_loc + "/app-created.txt")
        except Exception as e:
            fmlogging.debug(e)
            
        if not gae_app_created:
            app_obj.update_app_status(constants.SETTING_UP_APP)
            cwd = os.getcwd()
            app_dir = self.app_dir
            app_name = self.app_name
            app_version = self.app_version
            cont_name = app_name + "-" + app_version + "-" + constants.GOOGLE_APP_CREATE_CONT_SUF
            fmlogging.debug("Container name that will be used in building:%s" % cont_name)

            os.chdir(app_dir + "/" + app_name)
            build_cmd = ("docker build -t {name} -f Dockerfile.first_time . ").format(name=cont_name)
            fmlogging.debug("Docker build command:%s" % build_cmd)

            try:
                out = subprocess.Popen(build_cmd, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, shell=True).communicate()[0]

                fmlogging.debug(out)
                user_email = self.task_def.cloud_data['user_email']
                project_id = self.task_def.cloud_data['project_id']
                fp = open(df_first_time_loc + "/app-created.txt", "w")
                fp.write("%s %s %s" % (app_name, user_email, project_id))
                fp.close()

                # Remove first time container image
                cont_name = self.app_name + "-" + self.app_version + "-" + constants.GOOGLE_APP_CREATE_CONT_SUF
                self.docker_handler.stop_container(cont_name, "Stopping app create container")
                self.docker_handler.remove_container(cont_name, "Removing app create container")
                self.docker_handler.remove_container_image(cont_name, "Removing app create container image")

            except Exception as e:
                fmlogging.debug(e)
                fmlogging.debug("Probably gae app was already created.")

            os.chdir(cwd)

    def _build_app_container(self, app_obj):
        app_obj.update_app_status(constants.BUILDING_APP)
        cwd = os.getcwd()
        app_dir = self.task_def.app_data['app_location']
        app_name = self.task_def.app_data['app_name']
        os.chdir(app_dir + "/" + app_name)

        cont_name = app_obj.get_cont_name()
        fmlogging.debug("Container name that will be used in building:%s" % cont_name)

        build_cmd = ("docker build -t {name} . ").format(name=cont_name)
        fmlogging.debug("Docker build command:%s" % build_cmd)

        try:
            err, _ = self.docker_handler.build_ct_image(cont_name, "Dockerfile")
            os.chdir(cwd)
            if err and err.lower().index("error") >= 0:
                app_obj.update_app_status("ERROR:%s" % err)
        except Exception as e:
            fmlogging.error(e)
            raise e

    def build_for_delete(self, info):
        docker_file_name = "Dockerfile.delete"
        cont_name = ''
        cwd = os.getcwd()
        work_dir = ''
        if info['app_name']:
            fmlogging.debug("Google builder called for delete of app:%s" % info['app_name'])

            app_name = info['app_name']
            app_version = info['app_version']
            work_dir = (constants.APP_STORE_PATH + "/{app_name}/{app_version}/{app_name}").format(app_name=app_name,
                                                                                                 app_version=app_version)
            cont_name = app_name + "-delete"
        if info['service_name']:
            service_name = info['service_name']
            service_version = info['service_version']
            if not work_dir:
                work_dir = (constants.SERVICE_STORE_PATH + "/{service_name}/{service_version}/{service_name}").format(service_name=service_name,
                                                                                                                      service_version=service_version)
            if not cont_name:
                cont_name = service_name + "-delete"
        os.chdir(work_dir)
        build_cmd = ("docker build -t {cont_name} -f {docker_file_name} .").format(cont_name=cont_name,
                                                                                   docker_file_name=docker_file_name)
        fmlogging.debug("Build cmd:%s" % build_cmd)
        os.system(build_cmd)

        self.docker_handler.remove_container_image(cont_name, "Deleting container image created to perform delete action")

        os.chdir(cwd)

    def build_for_logs(self, info):
        fmlogging.debug("Google builder called for getting app logs of app:%s" % info['app_name'])

        app_name = info['app_name']
        app_version = info['app_version']
        app_dir = (constants.APP_STORE_PATH + "/{app_name}/{app_version}/{app_name}").format(app_name=app_name,
                                                                                             app_version=app_version)
        cwd = os.getcwd()
        os.chdir(app_dir)

        cont_name = app_name + "-get-logs"
        docker_file_name = "Dockerfile.logs"
        #build_cmd = ("docker build -t {cont_name} -f {docker_file_name} . &> ../{app_version}{runtime_log}").format(cont_name=cont_name,
        #                                                                                                         docker_file_name=docker_file_name,
        #                                                                                                         app_version=app_version,
        #                                                                                                         runtime_log=constants.RUNTIME_LOG)
        build_cmd = ("docker build -t {cont_name} -f {docker_file_name} . ").format(cont_name=cont_name,
                                                                                    docker_file_name=docker_file_name)

        fmlogging.debug("Build cmd:%s" % build_cmd)

        os.system(build_cmd)

        os.chdir(cwd)

    def build(self, build_type, build_name):
        if build_type == 'service':
            fmlogging.debug("Google builder called for service")

            for serv in self.task_def.service_data:
                serv_handler = self.services[serv['service']['type']]
                # Invoke public interface
                serv_handler.build_instance_artifacts()
        elif build_type == 'app':
            fmlogging.debug("Google builder called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            try:
                self._build_app_container(app_obj)
                self._build_first_time_container(app_obj)
            except Exception as e:
                fmlogging.error(e)
                raise e
        else:
            fmlogging.debug("Build type %s not supported." % build_type)
        
