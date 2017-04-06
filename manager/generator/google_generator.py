'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com>, December 13, 2016
'''

import ast
import logging
import os

from common import app
from common import docker_lib
from common import service
from common import utils
from common import constants
from common import fm_logger

from manager.service_handler.mysql import google_handler as gh

fmlogging = fm_logger.Logging()

GOOGLE_CREDS_PATH = constants.APP_STORE_PATH + "/google-creds"


class GoogleGenerator(object):

    def __init__(self, task_def):
        self.task_def = task_def
        self.instance_name = ''
        self.instance_version = ''
        self.instance_prov_workdir = ''

        if task_def.app_data:
            self.app_type = task_def.app_data['app_type']
            self.app_dir = task_def.app_data['app_location']
            self.app_name = task_def.app_data['app_name']
            self.entry_point = app.App(task_def.app_data).get_entrypoint_file_name()
            if 'app_variables' in task_def.app_data:
                self.app_variables = task_def.app_data['app_variables']

        self.services = {}
        if task_def.service_data:
            self.service_obj = service.Service(task_def.service_data[0])
            self.service_details = ''

            if self.service_obj.get_service_type() == 'mysql':
                self.services['mysql'] = gh.MySQLServiceHandler(self.task_def)

        self.docker_handler = docker_lib.DockerLib()
        
    def _get_app_yaml(self):
        app_yaml = ("runtime: python27 \n"
                    "api_version: 1 \n"
                    "threadsafe: true \n"
                    "\n"
                    "libraries: \n"
                    "- name: MySQLdb \n"
                    "  version: \"latest\" \n"
                    "\n"
                    "handlers: \n"
                    "- url: /static \n"
                    "  static_dir: static \n"
                    "- url: /.* \n"
                    )
        return app_yaml

    def _generate_app_yaml_delete(self, app_dir):
        app_yaml = self._get_app_yaml()
        app_yaml = app_yaml + ("  script: blank.app \n")
        fp = open(app_dir + "/app.yaml", "w")
        fp.write(app_yaml)
        fp.close()

    def _generate_app_yaml(self, app_deploy_dir, service_ip_dict):
        app_yaml = self._get_app_yaml()
        app_yaml = app_yaml + ("  script: {app_entry_point}.app \n"
                               "\n").format(app_entry_point=self.entry_point)

        if service_ip_dict:
            print_prefix = "    "
            env_key_suffix = ": "
            app_yaml_env_vars = utils.get_env_vars_string(self.task_def,
                                                          service_ip_dict,
                                                          self.app_variables,
                                                          self.services,
                                                          print_prefix,
                                                          env_key_suffix)

            app_yaml = app_yaml + ("env_variables:\n") + app_yaml_env_vars

        if 'env_variables' in self.task_def.app_data:
            env_var_obj = self.task_def.app_data['env_variables']
            env_vars = ''
            app_yaml = app_yaml + ("env_variables:\n")
            if env_var_obj:
                for key, value in env_var_obj.iteritems():
                        env_vars = env_vars + ("    {key}: {value}\n").format(key=key, value=value)
                app_yaml = app_yaml + env_vars

        fp = open(app_deploy_dir + "/app.yaml", "w")
        fp.write(app_yaml)
        fp.close()

    def _generate_lib_dir(self, app_deploy_dir):
        if os.path.exists(app_deploy_dir + "/requirements.txt"):
            cwd = os.getcwd()
            os.chdir(app_deploy_dir)
            generate_lib_cmd = ("pip install -t lib -r requirements.txt")
            fmlogging.debug("Generating Python application libs:%s" % generate_lib_cmd)
            os.system(generate_lib_cmd)
            os.chdir(cwd)

    def _generate_appengine_config(self, app_deploy_dir):
        if os.path.exists(app_deploy_dir + "/requirements.txt"):
            appengine_config = ("from google.appengine.ext import vendor \n\n"
                                "vendor.add('lib')")
            fp = open(app_deploy_dir + "/appengine_config.py", "w")
            fp.write(appengine_config)
            fp.close()

    def _check_if_first_time_app_deploy(self, app_name, user_email, project_id):
        df_first_time_loc = self.app_dir[:self.app_dir.rfind("/")]
        if not os.path.exists(df_first_time_loc + "/app-created.txt"):
            return True
        else:
            # check if an app_name has been created for user_email, project_id
            # by checking existence of following line:
            # app_name, user_email, project_id
            f = open(df_first_time_loc + "/app-created.txt", "r")
            all_lines = f.readlines()
            first_time_app = True
            for line in all_lines:
                parts = line.split(" ")
                if parts[0] == app_name and parts[1] == user_email and \
                    parts[2] == project_id:
                    first_time_app = False
                    break
            return first_time_app
    
    def _get_region(self):
        if os.path.exists(GOOGLE_CREDS_PATH + "/app_details.txt"):
            fp = open(GOOGLE_CREDS_PATH + "/app_details.txt", "r")
            lines = fp.readlines()
            for line in lines:
                if line.find("Region") >= 0:
                    parts = line.split(":")
                    region = parts[1].rstrip().lstrip()
        if not region:
            region = 'us-central' #default region
        return region

    def _generate_docker_file(self, app_deploy_dir):

        cmd_1 = ("RUN sed -i 's/{pat}access_token{pat}.*/{pat}access_token{pat}/' credentials \n").format(pat="\\\"")

        cmd_2 = ("RUN sed -i \"s/{pat}access_token{pat}.*/{pat}access_token{pat}:{pat}$token{pat},/\" credentials \n").format(pat="\\\"")

        fmlogging.debug("Sed pattern:%s" % cmd_1)

        df = ("FROM lmecld/clis:gcloud \n"
              "RUN /google-cloud-sdk/bin/gcloud components install beta \n"
              "COPY . /src \n"
              "COPY google-creds/gcloud  /root/.config/gcloud \n"
              "WORKDIR /root/.config/gcloud \n"
              "{cmd_1}"
              "RUN token=`/google-cloud-sdk/bin/gcloud beta auth application-default print-access-token` \n"
              "{cmd_2}"
              "WORKDIR /src \n"
              "RUN /google-cloud-sdk/bin/gcloud config set account {user_email} \ \n"
              "    && /google-cloud-sdk/bin/gcloud config set project {project_id} \ \n"
              "    && /google-cloud-sdk/bin/gcloud config set app/use_appengine_api false \n"
             )

        user_email = self.task_def.cloud_data['user_email']
        project_id = self.task_def.cloud_data['project_id']
        first_time = self._check_if_first_time_app_deploy(self.app_name,
                                                          user_email,
                                                          project_id)
        region = self._get_region()
        if first_time:
            df1 = df + ("RUN /google-cloud-sdk/bin/gcloud beta app create --region {region}\n")
            df1 = df1.format(cmd_1=cmd_1, cmd_2=cmd_2, user_email=self.task_def.cloud_data['user_email'],
                             project_id=self.task_def.cloud_data['project_id'], region=region)

        df = df + ("ENTRYPOINT [\"/google-cloud-sdk/bin/gcloud\", \"app\", \"deploy\", \"--quiet\"] \n")

        df = df.format(cmd_1=cmd_1, cmd_2=cmd_2, user_email=self.task_def.cloud_data['user_email'],
                       project_id=self.task_def.cloud_data['project_id'])

        if first_time:
            df_first_time_loc = self.app_dir[:self.app_dir.rfind("/")]
            fmlogging.debug("First time app location:%s" % df_first_time_loc)
            first_time_df = open(app_deploy_dir + "/Dockerfile.first_time", "w")
            first_time_df.write(df1)
            first_time_df.close()

        fp = open(app_deploy_dir + "/Dockerfile", "w")
        fp.write(df)
        fp.close()

    def _generate_for_python_app(self, app_obj, service_ip_dict, service_info):
        app_deploy_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir,
                                                         app_name=self.app_name)
        utils.copy_google_creds(GOOGLE_CREDS_PATH, app_deploy_dir)
        self._generate_app_yaml(app_deploy_dir, service_ip_dict)
        self._generate_lib_dir(app_deploy_dir)
        self._generate_appengine_config(app_deploy_dir)
        self._generate_docker_file(app_deploy_dir)

    def generate_for_delete(self, info):
        work_dir = ''
        df = self.docker_handler.get_dockerfile_snippet('google')
        df = df + ("RUN /google-cloud-sdk/bin/gcloud config set account {user_email} \ \n"
              "    && /google-cloud-sdk/bin/gcloud config set project {project_id} \ \n"
              "    && /google-cloud-sdk/bin/gcloud config set app/use_appengine_api false \ \n")

        if info['app_name']:
            fmlogging.debug("Google generator called for delete for app:%s" % info['app_name'])

            app_name = info['app_name']
            app_version = info['app_version']
            work_dir = (constants.APP_STORE_PATH + "/{app_name}/{app_version}/{app_name}").format(app_name=app_name,
                                                                                                 app_version=app_version)
            self._generate_app_yaml_delete(work_dir)
            df = df + ("    && /google-cloud-sdk/bin/gcloud app deploy --quiet \ \n")

        if info['service_name']:
            service_name = info['service_name']
            service_version = info['service_version']
            if not work_dir:
                work_dir = (constants.SERVICE_STORE_PATH + "/{service_name}/{service_version}/{service_name}").format(service_name=service_name,
                                                                                                                      service_version=service_version)
            service_terminate_cmd = ''
            if service_name:
                parts = service_name.split("-")
                if parts[0] == 'mysql':
                    mysql_handler = gh.MySQLServiceHandler(self.task_def)
                    service_terminate_cmd = mysql_handler.get_terminate_cmd(info)
                    df = df + (" && {terminate_cmd}")

        cloud_details = ast.literal_eval(info['cloud_details'])
        user_email = cloud_details['user_email']
        project_id = cloud_details['project_id']

        if service_terminate_cmd:
            df = df.format(user_email=user_email, project_id=project_id, terminate_cmd=service_terminate_cmd)
        else:
            df = df.format(user_email=user_email, project_id=project_id)

        fp = open(work_dir + "/Dockerfile.delete", "w")
        fp.write(df)
        fp.flush()
        fp.close()

    def generate_for_logs(self, info):
        fmlogging.debug("Google generator called for getting app logs for app:%s" % info['app_name'])

        app_name = info['app_name']
        app_version = info['app_version']
        app_dir = (constants.APP_STORE_PATH + "/{app_name}/{app_version}/{app_name}").format(app_name=app_name,
                                                                                             app_version=app_version)

        df = self.docker_handler.get_dockerfile_snippet('google')
        df = df + ("RUN /google-cloud-sdk/bin/gcloud config set account {user_email} \ \n"
              "    && /google-cloud-sdk/bin/gcloud config set project {project_id} \ \n"
              "    && /google-cloud-sdk/bin/gcloud config set app/use_appengine_api false \n")

        df = df + ("ENTRYPOINT [\"/google-cloud-sdk/bin/gcloud\", \"beta\", \"logging\", \"read\", \"request_log\"] \n")

        cloud_details = ast.literal_eval(info['cloud_details'])

        user_email = cloud_details['user_email']
        project_id = cloud_details['project_id']
        df = df.format(user_email=user_email, project_id=project_id)

        fmlogging.debug("Dockerfile dir:%s" % app_dir)
        docker_file = open(app_dir + "/Dockerfile.logs", "w")
        docker_file.write(df)
        docker_file.flush()
        docker_file.close()

    def _sanity_check(self, app_obj):
        gcloud_path = GOOGLE_CREDS_PATH + "/gcloud"
        app_details_path = GOOGLE_CREDS_PATH + "/app_details.txt"
        sanity_check_passed = False
        if os.path.exists(GOOGLE_CREDS_PATH):
            if os.path.exists(gcloud_path) and not os.listdir(gcloud_path) == "":
                if os.path.exists(app_details_path) and os.stat(app_details_path).st_size > 0:
                    sanity_check_passed = True
        if not sanity_check_passed:
            app_obj.update_app_status("DEPLOYMENT_SANITY_CHECK_FAILURE. \n (Do Google cloud setup again.)")
            raise Exception()

    def generate(self, build_type, service_ip_dict, service_info):
        if build_type == 'service':
            fmlogging.debug("Google generator called for service")
            if self.task_def.app_data:
                app_obj = app.App(self.task_def.app_data)
                app_obj.update_app_status("GENERATING Google ARTIFACTS for Cloud SQL instance")
            for serv in self.task_def.service_data:
                serv_handler = self.services[serv['service']['type']]
                # Invoke public interface
                serv_handler.generate_instance_artifacts()
        else:
            fmlogging.debug("Google generator called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            # Sanity check for google
            self._sanity_check(app_obj)
            app_obj.update_app_status("GENERATING Google ARTIFACTS for App")
            if self.app_type == 'python':
                self._generate_for_python_app(app_obj, service_ip_dict, service_info)
            else:
                print("Application of type %s not supported." % self.app_type)
        return 0