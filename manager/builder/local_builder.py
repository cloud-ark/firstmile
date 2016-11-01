'''
Created on Oct 26, 2016

@author: devdatta
'''
import os
from io import BytesIO
from docker import Client
from common import app

class LocalBuilder(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')
        
    def _build_service_container(self):
        pass
    
    def _build_app_container(self, app_obj):
        cwd = os.getcwd()
        app_dir = self.task_def.app_data['app_location']
        app_name = self.task_def.app_data['app_name']
        os.chdir(app_dir + "/" + app_name)

        cont_name = app_obj.get_cont_name()
        
        build_cmd = ("docker build -t {name} .").format(name=cont_name)
        os.system(build_cmd)
                
        os.chdir(cwd)
        
    def build(self, build_type, build_name):
        print("Local builder called for app %s" % self.task_def.app_data['app_name'])
        
        if build_type == 'service':
            self._build_service_container()
        elif build_type == 'app':
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status("Starting app build")
            self._build_app_container(app_obj)
        return 0
