'''
Created on Oct 26, 2016

@author: devdatta
'''
import logging
from common import service
from common import app
from common import utils
from common import constants

from manager.service_handler.mysql import local_handler as lh


class LocalGenerator(object):

    def __init__(self, task_def):
        self.task_def = task_def
        if self.task_def.app_data:
            self.app_type = task_def.app_data['app_type']
            self.app_dir = task_def.app_data['app_location']
            self.app_name = task_def.app_data['app_name']
            self.app_port = task_def.app_data['app_port']
            if 'app_variables' in task_def.app_data:
                self.app_variables = task_def.app_data['app_variables']

        self.services = {}

        if task_def.service_data:
            self.service_obj = service.Service(task_def.service_data[0])
            if self.service_obj.get_service_type() == 'mysql':
                self.services['mysql'] = lh.MySQLServiceHandler(self.task_def)

    def _generate_for_service(self):
        pass

    def _generate_for_python_app(self, service_ip_dict):

        df_env_vars = ''
        if bool(service_ip_dict):
            print_prefix = "ENV "
            env_key_suffix = " "
            df_env_vars = utils.get_env_vars_string(self.task_def,
                                                    service_ip_dict,
                                                    self.app_variables,
                                                    self.services,
                                                    print_prefix,
                                                    env_key_suffix)

        entry_point = self.task_def.app_data['entry_point']

        df = ''
        if bool(service_ip_dict):
            df = ("FROM ubuntu:14.04\n"
                  "RUN apt-get update -y \ \n"
                  "    && apt-get install -y python-setuptools python-pip\n"
                  "ADD requirements.txt /src/requirements.txt\n"
                  "RUN cd /src; pip install -r requirements.txt\n"
                  "ADD . /src\n"
                  "EXPOSE {app_port}\n"
                  ).format(app_port=self.app_port)
            df = df + df_env_vars
            df = df + ("CMD [\"python\", \"/src/{entry_point}\"]").format(entry_point=entry_point)
        else:
            df = ("FROM ubuntu:14.04\n"
                  "RUN apt-get update -y \ \n"
                  "    && apt-get install -y python-setuptools python-pip\n"
                  "ADD requirements.txt /src/requirements.txt\n"
                  "RUN cd /src; pip install -r requirements.txt\n"
                  "ADD . /src\n"
                  "EXPOSE {app_port}\n"
                  ).format(app_port=self.app_port)

            if 'env_variables' in self.task_def.app_data:
                env_var_obj = self.task_def.app_data['env_variables']
                env_vars = ''
                if env_var_obj:
                    for key, value in env_var_obj.iteritems():
                        env_vars = env_vars + ("ENV {key} {value}\n").format(key=key, value=value)
                    df = df + env_vars

            df = df +  ("CMD [\"python\", \"/src/{entry_point}\"]").format(entry_point=entry_point)

        logging.debug("App dir: %s" % self.app_dir)
        docker_file_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                          app_name=self.app_name)
        logging.debug("Dockerfile dir:%s" % docker_file_dir)
        docker_file = open(docker_file_dir + "/Dockerfile", "w")
        docker_file.write(df)
        docker_file.close()

    def generate_for_delete(self, info):
        logging.debug("Local generator called for delete for app:%s" % info['app_name'])

    def generate(self, generate_type, service_ip_dict):
        if generate_type == 'service':
            self._generate_for_service()
        elif generate_type == 'app':
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status("GENERATING artifacts for local deployment")
            logging.debug("Local generator called for app %s" %
                          self.task_def.app_data['app_name'])
            if self.app_type == 'python':
                self._generate_for_python_app(service_ip_dict)
            else:
                print("Application of type %s not supported." % self.app_type)
        return 0