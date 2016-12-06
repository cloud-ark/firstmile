'''
Created on Dec 6, 2016

@author: devdatta
'''
import logging
import os
from common import app

from os.path import expanduser

home_dir = expanduser("~")

APP_STORE_PATH = ("{home_dir}/.lme/data/deployments").format(home_dir=home_dir)
AWS_CREDS_PATH = APP_STORE_PATH + "/aws-creds"


class AWSGenerator(object):

    def __init__(self, task_def):
        self.task_def = task_def
        self.app_type = task_def.app_data['app_type']
        self.app_dir = task_def.app_data['app_location']
        self.app_name = task_def.app_data['app_name']

    def _generate_for_python_app(self, app_obj, service_ip_dict):

        app_deploy_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                         app_name=self.app_name)

        # Copy aws-creds to the app directory
        cp_cmd = ("cp -r {aws_creds_path} {app_deploy_dir}/.").format(aws_creds_path=AWS_CREDS_PATH,
                                                                    app_deploy_dir=app_deploy_dir)
        
        logging.debug("Copying aws-creds directory..")
        logging.debug(cp_cmd)
        
        os.system(cp_cmd)
        
        env_name = app_obj.get_cont_name()
        logging.debug("Environment name:%s" % env_name)

        # Generate Dockerfile
        df = ("FROM ubuntu:14.04\n"
              "RUN apt-get update && apt-get install -y \ \n"
              "    python-setuptools python-pip\n"
              "RUN pip install awsebcli==3.7.7\n"
              "RUN pip install awscli==1.10.63\n"
              "COPY . /src \n"
              "WORKDIR /src \n"
              "RUN cp -r aws-creds $HOME/.aws \n"
              "RUN mv Dockerfile Dockerfile.bak \n"
              "ENTRYPOINT [\"eb\", \"create\", \"{env_name}\", \"-c\", \"{env_name}\"]  \n"
            ).format(aws_creds_path=AWS_CREDS_PATH, env_name=env_name)

        logging.debug("App dir: %s" % self.app_dir)
        docker_file_dir = app_deploy_dir
        logging.debug("Dockerfile dir:%s" % docker_file_dir)
        docker_file = open(docker_file_dir + "/Dockerfile", "w")
        docker_file.write(df)
        docker_file.close()

        # Generate .elasticbeanstalk/config.yml
        beanstalk_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                        app_name=self.app_name)
        os.mkdir(beanstalk_dir + "/.elasticbeanstalk")
        fp = open(beanstalk_dir + "/.elasticbeanstalk/config.yml", "w")
        ebconfig =("branch-defaults:\n"
                   "  default:\n"
                   "    environment: {env_name} \n"
                   "    group_suffix: null \n"
                   "global:\n"
                   "  application_name: {app_name} \n"
                   "  default_ec2_keyname: null \n"
                   "  default_platform: Python 3.4 (Preconfigured - Docker) \n"
                   "  default_region: us-west-2 \n"
                   "  profile: null \n"
                   "  sc: null \n"
            ).format(env_name=env_name, app_name=self.app_name)
        fp.write(ebconfig)
        fp.close()
        
    def generate(self, service_ip_dict):
        logging.debug("Local generator called for app %s" %
                      self.task_def.app_data['app_name'])
        
        app_obj = app.App(self.task_def.app_data)
        app_obj.update_app_status("status::GENERATING AWS ARTIFACTS")

        if self.app_type == 'python':
            self._generate_for_python_app(app_obj, service_ip_dict)
        else:
            print("Application of type %s not supported." % self.app_type)        
        return 0