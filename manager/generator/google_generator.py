'''
Created on Dec 13, 2016

@author: devdatta
'''
import logging
import os

from common import app

from os.path import expanduser

home_dir = expanduser("~")

APP_STORE_PATH = ("{home_dir}/.lme/data/deployments").format(home_dir=home_dir)
GOOGLE_CREDS_PATH = APP_STORE_PATH + "/google-creds"


class GoogleGenerator(object):

    def __init__(self, task_def):
        self.task_def = task_def
        self.app_type = task_def.app_data['app_type']
        self.app_dir = task_def.app_data['app_location']
        self.app_name = task_def.app_data['app_name']
        self.entry_point = app.App(task_def.app_data).get_entrypoint_file_name()

        # set the name of the entry_point
        if task_def.service_data:
            self.service_details = task_def.service_data[0]['service_details']
        
    def _generate_app_yaml(self, app_deploy_dir, service_ip_dict):
        app_yaml = ("runtime: python27 \n"
                    "api_version: 1 \n"
                    "threadsafe: true \n"
                    "\n"
                    "handlers: \n"
                    "- url: /static \n"
                    "  static_dir: static \n"
                    "- url: /.* \n"
                    "  script: {app_entry_point}.app \n"
                    "\n").format(app_entry_point=self.entry_point)

        if service_ip_dict:
            # Read the values for username and password from lme.conf
            # Read the key names and value for db_name to use in env_vars from service_info object
            username_val = 'lmeroot'
            password_val = 'lme123'
            app_yaml = app_yaml + ("env_variables:\n"
                                   "    {username_key}: '{username_val}' \n"
                                   "    {host_key}: '{service_ip}' \n"
                                   "    {db_key}: '{db_name}' \n"
                                   "    {password_key}: '{password_val}' \n"
                                   ).format(username_key=self.service_details['user_var'],
                                            username_val=username_val,
                                            host_key=self.service_details['host_var'],
                                            service_ip=service_ip_dict['mysql-service'],
                                            db_key=self.service_details['db_var'],
                                            db_name=self.service_details['db_name'],
                                            password_key=self.service_details['password_var'],
                                            password_val=password_val)

        fp = open(app_deploy_dir + "/app.yaml", "w")
        fp.write(app_yaml)
        fp.close()

    def _generate_lib_dir(self, app_deploy_dir):
        if os.path.exists(app_deploy_dir + "/requirements.txt"):
            cwd = os.getcwd()
            os.chdir(app_deploy_dir)
            generate_lib_cmd = ("pip install -t lib -r requirements.txt")
            logging.debug("Generating Python application libs:%s" % generate_lib_cmd)
            os.system(generate_lib_cmd)
            os.chdir(cwd)

    def _generate_appengine_config(self, app_deploy_dir):
        if os.path.exists(app_deploy_dir + "/requirements.txt"):
            appengine_config = ("from google.appengine.ext import vendor \n\n"
                                "vendor.add('lib')")
            fp = open(app_deploy_dir + "/appengine_config.py", "w")
            fp.write(appengine_config)
            fp.close()

    def _check_if_first_time_app_deploy(self):
        df_first_time_loc = self.app_dir[:self.app_dir.rfind("/")]
        if not os.path.exists(df_first_time_loc + "/app-created.txt"):
            return True
        else:
            return False
    
    def _generate_docker_file(self, app_deploy_dir):

        cmd_1 = ("RUN sed -i 's/{pat}access_token{pat}.*/{pat}access_token{pat}/' credentials \n").format(pat="\\\"")

        cmd_2 = ("RUN sed -i \"s/{pat}access_token{pat}.*/{pat}access_token{pat}:{pat}$token{pat},/\" credentials \n").format(pat="\\\"")

        logging.debug("Sed pattern:%s" % cmd_1)

        df = ("FROM ubuntu:14.04 \n"
              "RUN apt-get update && apt-get install -y wget python \n"
              "RUN sudo wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-126.0.0-linux-x86_64.tar.gz && \ \n"
              "    sudo gunzip google-cloud-sdk-126.0.0-linux-x86_64.tar.gz && \ \n"
              "    sudo tar -xvf google-cloud-sdk-126.0.0-linux-x86_64.tar \n"
              "RUN /google-cloud-sdk/bin/gcloud components install beta \n"
              "COPY . /src \n"
              "COPY google-creds/gcloud  /root/.config/gcloud \n"
              "WORKDIR /root/.config/gcloud \n"
              "{cmd_1}"
              "RUN token=`/google-cloud-sdk/bin/gcloud beta auth application-default print-access-token` \n"
              "{cmd_2}"
              "WORKDIR /src \n"
              "RUN /google-cloud-sdk/bin/gcloud config set account {user_email} \n"
              "RUN /google-cloud-sdk/bin/gcloud config set project {project_id} \n"
             )

        first_time = self._check_if_first_time_app_deploy()
        if first_time:
            df1 = df + ("RUN /google-cloud-sdk/bin/gcloud beta app create --region us-central \n")
            df1 = df1.format(cmd_1=cmd_1, cmd_2=cmd_2, user_email=self.task_def.app_data['user_email'],
                             project_id=self.task_def.app_data['project_id'])

        df = df + ("ENTRYPOINT [\"/google-cloud-sdk/bin/gcloud\", \"app\", \"deploy\", \"--quiet\"] \n")

        df = df.format(cmd_1=cmd_1, cmd_2=cmd_2, user_email=self.task_def.app_data['user_email'],
                       project_id=self.task_def.app_data['project_id'])

        if first_time:
            df_first_time_loc = self.app_dir[:self.app_dir.rfind("/")]
            logging.debug("First time app location:%s" % df_first_time_loc)
            first_time_df = open(app_deploy_dir + "/Dockerfile.first_time", "w")
            first_time_df.write(df1)
            first_time_df.close()

        fp = open(app_deploy_dir + "/Dockerfile", "w")
        fp.write(df)
        fp.close()

    def _copy_creds_to_app_dir(self):
        app_deploy_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                         app_name=self.app_name)

        # Copy google-creds to the app directory
        cp_cmd = ("cp -r {google_creds_path} {app_deploy_dir}/.").format(google_creds_path=GOOGLE_CREDS_PATH,
                                                                         app_deploy_dir=app_deploy_dir)
        
        logging.debug("Copying google-creds directory..")
        logging.debug(cp_cmd)

        os.system(cp_cmd)

    def _generate_for_python_app(self, app_obj, service_ip_dict, service_info):
        app_deploy_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir,
                                                         app_name=self.app_name)
        self._copy_creds_to_app_dir()
        self._generate_app_yaml(app_deploy_dir, service_ip_dict)
        self._generate_lib_dir(app_deploy_dir)
        self._generate_appengine_config(app_deploy_dir)
        self._generate_docker_file(app_deploy_dir)

    def _generate_docker_file_for_service(self, app_obj):
        logging.debug("Generating Docker file that will give new access token.")
        app_obj.update_app_status("status::GENERATING Google ARTIFACTS for MySQL service")

        self._copy_creds_to_app_dir()

        app_deploy_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir,
                                                         app_name=self.app_name)
        cmd_1 = ("RUN sed -i 's/{pat}access_token{pat}.*/{pat}access_token{pat}/' credentials \n").format(pat="\\\"")
        df = ("FROM ubuntu:14.04 \n"
              "RUN apt-get update && apt-get install -y wget python \n"
              "RUN sudo wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-126.0.0-linux-x86_64.tar.gz && \ \n"
              "    sudo gunzip google-cloud-sdk-126.0.0-linux-x86_64.tar.gz && \ \n"
              "    sudo tar -xvf google-cloud-sdk-126.0.0-linux-x86_64.tar \n"
              "RUN /google-cloud-sdk/bin/gcloud components install beta \n"
              "COPY . /src \n"
              "COPY google-creds/gcloud  /root/.config/gcloud \n"
              "WORKDIR /root/.config/gcloud \n"
              #"{cmd_1}"
              "RUN token=`/google-cloud-sdk/bin/gcloud beta auth application-default print-access-token` && \ \n"
              "    echo $token > /src/access_token.txt"
            ).format(cmd_1=cmd_1)

        fp = open(app_deploy_dir + "/Dockerfile.access_token", "w")
        fp.write(df)
        fp.close()

    def generate(self, build_type, service_ip_dict, service_info):
        logging.debug("Google generator called for app %s" %
                      self.task_def.app_data['app_name'])
        
        if build_type == 'service':
            app_obj = app.App(self.task_def.app_data)
            self._generate_docker_file_for_service(app_obj)
        else:
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status("status::GENERATING Google ARTIFACTS for App")
            if self.app_type == 'python':
                self._generate_for_python_app(app_obj, service_ip_dict, service_info)
            else:
                print("Application of type %s not supported." % self.app_type)
        return 0