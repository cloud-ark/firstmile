'''
Created on Dec 18, 2016

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

class GoogleBuilder(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.app_dir = task_def.app_data['app_location']
        self.app_name = task_def.app_data['app_name']
        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')

    def _build_service_container(self):
        logging.debug("Building service container")
        app_deploy_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                         app_name=self.app_name)        

        cwd = os.getcwd()
        os.chdir(app_deploy_dir)
        cmd = "docker build -t google-access-token-cont -f Dockerfile.access_token . "
        try:
            os.system(cmd)
        except Exception as e:
            print(e)
        os.chdir(cwd)

    def _build_first_time_container(self, app_obj):
        df_first_time_loc = self.app_dir[:self.app_dir.rfind("/")]
        
        try:
            gae_app_created = os.path.isfile(df_first_time_loc + "/app-created.txt")
        except Exception as e:
            logging.debug(e)
            
        if not gae_app_created:
            app_obj.update_app_status("status::BUILDING FIRST TIME APP CONTAINER")
            cwd = os.getcwd()
            app_dir = self.task_def.app_data['app_location']
            app_name = self.task_def.app_data['app_name']
            cont_name = app_name + "-app-create-cont"
            logging.debug("Container name that will be used in building:%s" % cont_name)

            os.chdir(app_dir + "/" + app_name)
            build_cmd = ("docker build -t {name} -f Dockerfile.first_time . ").format(name=cont_name)
            logging.debug("Docker build command:%s" % build_cmd)

            try:
                result = subprocess.check_output(build_cmd, shell=True)
                logging.debug(result)
            except Exception as e:
                logging.debug(e)
                logging.debug("Probably gae app was already created.")

            os.chdir(cwd)

            fp = open(df_first_time_loc + "/app-created.txt", "w")
            fp.write("Google App Engine app created for app %s" % app_name)
            fp.close()

    def _build_app_container(self, app_obj):
        app_obj.update_app_status("status::BUILDING APP CONTAINER")
        cwd = os.getcwd()
        app_dir = self.task_def.app_data['app_location']
        app_name = self.task_def.app_data['app_name']
        os.chdir(app_dir + "/" + app_name)

        cont_name = app_obj.get_cont_name()
        logging.debug("Container name that will be used in building:%s" % cont_name)

        build_cmd = ("docker build -t {name} . ").format(name=cont_name)
        logging.debug("Docker build command:%s" % build_cmd)

        result = subprocess.check_output(build_cmd, shell=True)
        logging.debug(result)

        os.chdir(cwd)

    def build(self, build_type, build_name):
        logging.debug("Google builder called for app %s" %
                      self.task_def.app_data['app_name'])
        
        if build_type == 'service':
            self._build_service_container()
        elif build_type == 'app':
            app_obj = app.App(self.task_def.app_data)
            self._build_app_container(app_obj)
            self._build_first_time_container(app_obj)
        else:
            logging.debug("Build type %s not supported." % build_type)
        
