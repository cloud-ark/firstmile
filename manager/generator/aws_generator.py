'''
Created on Dec 6, 2016

@author: devdatta
'''
import logging
import os
import stat as s

from common import app
from common import service
from common import utils

from manager.service_handler.mysql import aws_handler as awsh

from os.path import expanduser

home_dir = expanduser("~")

APP_STORE_PATH = ("{home_dir}/.lme/data/deployments").format(home_dir=home_dir)
AWS_CREDS_PATH = APP_STORE_PATH + "/aws-creds"


class AWSGenerator(object):

    def __init__(self, task_def):
        self.task_def = task_def

        if self.task_def.app_data:
            self.app_type = task_def.app_data['app_type']
            self.app_dir = task_def.app_data['app_location']
            self.app_name = task_def.app_data['app_name']
            self.entry_point = app.App(task_def.app_data).get_entrypoint_file_name()

        self.services = {}
        if task_def.service_data:
            self.service_obj = service.Service(task_def.service_data[0])
            self.service_details = ''

            if self.service_obj.get_service_type() == 'mysql':
                self.services['mysql'] = awsh.MySQLServiceHandler(self.task_def)
        
    def _generate_elasticbeanstalk_dir(self, service_info, env_name):
        # Generate .elasticbeanstalk/config.yml
        logging.debug("Inside _generate_elasticbeanstalk_dir")
        beanstalk_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                        app_name=self.app_name)
        os.mkdir(beanstalk_dir + "/.elasticbeanstalk")
        fp = open(beanstalk_dir + "/.elasticbeanstalk/config.yml", "w")
        default_platform = "default_platform: Python 3.4 (Preconfigured - Docker) \n"
        if service_info:
            default_platform = "default_platform: Docker 1.11.2 \n"
        ebconfig =("branch-defaults:\n"
                   "  default:\n"
                   "    environment: {env_name} \n"
                   "    group_suffix: null \n"
                   "global:\n"
                   "  application_name: {app_name} \n"
                   "  default_ec2_keyname: null \n"
                   "  {default_platform}"
                   "  default_region: us-west-2 \n"
                   "  profile: null \n"
                   "  sc: null \n"
            ).format(env_name=env_name, app_name=self.app_name, default_platform=default_platform)
        fp.write(ebconfig)
        fp.close()

    def _generate_ebextensions_dir(self, service_info):
        logging.debug("Inside _generate_ebextensions_dir")
        if service_info:
            ebextension_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                        app_name=self.app_name)
            os.mkdir(ebextension_dir + "/.ebextensions")
            fp = open(ebextension_dir + "/.ebextensions/setup.config", "w")
            setup_cfg = ("Resources:\n"
                         "  StartupSignupsTable:\n"
                         "    Type: AWS::DynamoDB::Table\n"
                         "    Properties:\n"
                         "      KeySchema:\n"
                         "        HashKeyElement:\n"
                         "          AttributeName: \"lme-db\" \n"
                         "          AttributeType: \"S\" \n"
                         "      ProvisionedThroughput:\n"
                         "        ReadCapacityUnits: 1\n"
                         "        WriteCapacityUnits: 1\n"
                         )
            fp.write(setup_cfg)
            fp.close()
    
    def _generate_platform_dockerfile(self, service_info):
        logging.debug("Inside _generate_platform_dockerfile")
        if service_info:
            app_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                        app_name=self.app_name)
            # Generate runapp.sh
            runapp_fp = open(app_dir + "/runapp.sh", "w")
            runapp = ("#!/bin/sh \n"
                      "export DB=$RDS_DB_NAME \n"
                      "export USER=$RDS_USERNAME \n"
                      "export PASSWORD=$RDS_PASSWORD \n"
                      "export HOST=$RDS_HOSTNAME \n"
                      "python /src/{entry_point} \n"
                      ).format(entry_point=self.entry_point + ".py")
            runapp_fp.write(runapp)
            runapp_fp.close()
            
            # Setting permission to 555
            permission = s.S_IRUSR | s.S_IRGRP | s.S_IROTH | s.S_IXUSR | s.S_IXGRP | s.S_IXOTH
            os.chmod(app_dir + "/runapp.sh", permission)

            # Generate Dockerfile
            fp = open(app_dir + "/Dockerfile.aws", "w")
            df = ("FROM ubuntu:14.04\n"
                  "RUN apt-get update && apt-get install -y \ \n"
                  "    python-setuptools python-pip git\n"
                  "ADD requirements.txt /src/requirements.txt \n"
                  "RUN cd /src; pip install -r requirements.txt \n"
                  "ADD . /src \n"
                  "EXPOSE 5000 \n"
                  "ENV DB $RDS_DB_NAME \n"
                  "ENV USER $RDS_USERNAME \n"
                  "ENV PASSWORD $RDS_PASSWORD \n"
                  "ENV HOST $RDS_HOSTNAME \n"
                  #"CMD [\"python\", \"/src/application.py\"]"
                  "CMD /src/runapp.sh"                  
                  )
            fp.write(df)
            fp.close()

    def _generate_for_python_app(self, app_obj, service_ip_dict, service_info):

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
        
        entrypt_cmd = ("ENTRYPOINT [\"eb\", \"create\", \"{env_name}\", \"-c\", "
                       "\"{env_name}\", \"--timeout\", \"20\"]  \n").format(env_name=env_name)
        dockerfile_maneuver = ("RUN mv Dockerfile Dockerfile.bak \n")
        if service_info:
            entrypt_cmd = ("ENTRYPOINT [\"eb\", \"create\", \"{env_name}\", \"-c\", "
                           "\"{env_name}\", \"-db\", \"--timeout\", \"20\"] \n").format(env_name=env_name)
            dockerfile_maneuver = ("RUN mv Dockerfile Dockerfile.bak \n"
                                   "RUN mv Dockerfile.aws Dockerfile \n")
            
        logging.debug("Entrypoint cmd:%s" % entrypt_cmd)
        logging.debug("Dockerfile maneuver:%s" % dockerfile_maneuver)
            
        # Generate Dockerfile
        df = ("FROM ubuntu:14.04\n"
              "RUN apt-get update && apt-get install -y \ \n"
              "    python-setuptools python-pip git groff\n"
              "RUN pip install awsebcli==3.7.7\n"
              "RUN pip install awscli==1.10.63\n"
              "COPY . /src \n"
              "WORKDIR /src \n"
              "RUN cp -r aws-creds $HOME/.aws \n"
              "{dockerfile_maneuver}"
              "{entrypt_cmd}"
            ).format(aws_creds_path=AWS_CREDS_PATH, dockerfile_maneuver=dockerfile_maneuver, entrypt_cmd=entrypt_cmd)

        logging.debug("App dir: %s" % self.app_dir)
        docker_file_dir = app_deploy_dir
        logging.debug("Dockerfile dir:%s" % docker_file_dir)
        docker_file = open(docker_file_dir + "/Dockerfile", "w")
        docker_file.write(df)
        docker_file.close()

        self._generate_elasticbeanstalk_dir(service_info, env_name)
        self._generate_ebextensions_dir(service_info)
        self._generate_platform_dockerfile(service_info)
        
    def generate(self, generate_type, service_ip_dict, service_info):
        if generate_type == 'service':
            logging.debug("AWS generator called for service")
            self.service_obj = service.Service(self.task_def.service_data[0])
            deploy_dir = self.service_obj.get_service_prov_work_location()
            # Copy aws-creds to the service deploy directory
            cp_cmd = ("cp -r {aws_creds_path} {deploy_dir}/.").format(aws_creds_path=AWS_CREDS_PATH,
                                                                      deploy_dir=deploy_dir)
        
            logging.debug("Copying aws-creds directory..")
            logging.debug(cp_cmd)
            os.system(cp_cmd)

            if self.task_def.app_data:
                app_obj = app.App(self.task_def.app_data)
                app_obj.update_app_status("GENERATING AWS ARTIFACTS for RDS instance")
            for serv in self.task_def.service_data:
                serv_handler = self.services[serv['service']['type']]
                utils.update_status(self.service_obj.get_status_file_location(),
                                    "GENERATING_ARTIFACTS_FOR_PROVISIONING_SERVICE_INSTANCE")

                # Invoke public interface
                serv_handler.generate_instance_artifacts()
        else:
            logging.debug("AWS generator called for app %s" %
                          self.task_def.app_data['app_name'])

            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status("GENERATING AWS ARTIFACTS")

            if self.app_type == 'python':
                self._generate_for_python_app(app_obj, service_ip_dict, service_info)
            else:
                print("Application of type %s not supported." % self.app_type)
        return 0