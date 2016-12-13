'''
Created on Dec 13, 2016

@author: devdatta
'''
import logging
import os
import stat as s

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
        
    def _generate_app_yaml(self, app_deploy_dir):
        app_yaml = ("runtime: python27 \n"
                    "api_version: 1 \n"
                    "threadsafe: true \n"
                    "\n"
                    "handlers: \n"
                    "- url: /static \n"
                    "  static_dir: static \n"
                    "- url: /.* \n"
                    "  script: application.app \n"
                    "")

        fp = open(app_deploy_dir + "/app.yaml", "w")
        fp.write(app_yaml)
        fp.close()

    def _generate_lib_dir(self, app_deploy_dir):
        cwd = os.getcwd()
        os.chdir(app_deploy_dir)

        generate_lib_cmd = ("pip install -t lib -r requirements.txt")
        logging.debug("Generating Python application libs:%s" % generate_lib_cmd)
        os.system(generate_lib_cmd)
        os.chdir(cwd)

    def _generate_appengine_config(self, app_deploy_dir):
        appengine_config = ("from google.appengine.ext import vendor \n\n"
                            "vendor.add('lib')")

        fp = open(app_deploy_dir + "/appengine_config.py", "w")
        fp.write(appengine_config)
        fp.close()
    
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
              #"RUN /google-cloud-sdk/bin/gcloud beta app create --region us-central \n"
              "ENTRYPOINT [\"/google-cloud-sdk/bin/gcloud\", \"app\", \"deploy\", \"--quiet\"] \n"
              ).format(cmd_1=cmd_1, cmd_2=cmd_2, user_email="cc1h499@gmail.com", project_id="hello-world-152322")

        fp = open(app_deploy_dir + "/Dockerfile", "w")
        fp.write(df)
        fp.close()

    def _generate_for_python_app(self, app_obj, service_ip_dict, service_info):

        app_deploy_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                         app_name=self.app_name)

        # Copy google-creds to the app directory
        cp_cmd = ("cp -r {google_creds_path} {app_deploy_dir}/.").format(google_creds_path=GOOGLE_CREDS_PATH,
                                                                         app_deploy_dir=app_deploy_dir)
        
        logging.debug("Copying google-creds directory..")
        logging.debug(cp_cmd)

        os.system(cp_cmd)
        self._generate_app_yaml(app_deploy_dir)
        self._generate_lib_dir(app_deploy_dir)
        self._generate_appengine_config(app_deploy_dir)
        self._generate_docker_file(app_deploy_dir)

    def generate(self, service_ip_dict, service_info):
        logging.debug("Google generator called for app %s" %
                      self.task_def.app_data['app_name'])
        
        app_obj = app.App(self.task_def.app_data)
        app_obj.update_app_status("status::GENERATING Google ARTIFACTS")

        if self.app_type == 'python':
            self._generate_for_python_app(app_obj, service_ip_dict, service_info)
        else:
            print("Application of type %s not supported." % self.app_type)        
        return 0


        