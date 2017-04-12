'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com>, December 6, 2016
'''

import logging
import os
import stat as s

from common import app
from common import service
from common import utils
from common import docker_lib
from common import constants
from common import fm_logger

from manager.service_handler.mysql import aws_handler as awsh

from random import randint

fmlogging = fm_logger.Logging()

AWS_CREDS_PATH = constants.APP_STORE_PATH + "/aws-creds"


class AWSGenerator(object):

    def __init__(self, task_def):
        self.task_def = task_def
        self.instance_name = ''
        self.instance_version = ''
        self.app_name = ''
        self.app_version = ''
        self.services = {}
        self.service_handler = ''
        self.instance_prov_workdir = ''
        self.app_variables = ''

        # Set values using service_data first
        if task_def.service_data:
            self.service_obj = service.Service(task_def.service_data[0])
            self.instance_prov_workdir = self.service_obj.get_service_prov_work_location()
            self.instance_name = self.service_obj.get_service_name()
            self.instance_version = self.service_obj.get_service_version()

            if self.service_obj.get_service_type() == 'mysql':
                self.services['mysql'] = awsh.MySQLServiceHandler(self.task_def)

        # If app_data is present overwrite the previously set values
        if self.task_def.app_data:
            self.app_type = task_def.app_data['app_type']
            self.app_dir = task_def.app_data['app_location']
            self.app_name = task_def.app_data['app_name']
            self.app_version = task_def.app_data['app_version']
            self.instance_prov_workdir = task_def.app_data['app_location'] + "/" + task_def.app_data['app_name']
            self.entry_point = app.App(task_def.app_data).get_entrypoint_file_name()

            if 'app_variables' in task_def.app_data:
                self.app_variables = task_def.app_data['app_variables']

        self.deploy_dir = self.instance_prov_workdir

        self.docker_handler = docker_lib.DockerLib()
        
    def _generate_elasticbeanstalk_dir(self, service_info, env_name):
        # Generate .elasticbeanstalk/config.yml
        fmlogging.debug("Inside _generate_elasticbeanstalk_dir")
        beanstalk_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                        app_name=self.app_name)
        os.mkdir(beanstalk_dir + "/.elasticbeanstalk")
        fp = open(beanstalk_dir + "/.elasticbeanstalk/config.yml", "w")
        default_platform = "default_platform: Python 3.4 (Preconfigured - Docker) \n"
        region = utils.get_aws_region()
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
                   "  default_region: {region} \n"
                   "  profile: null \n"
                   "  sc: null \n"
            ).format(env_name=env_name, app_name=self.app_name,
                     default_platform=default_platform,
                     region=region)
        fp.write(ebconfig)
        fp.close()

    def _generate_ebextensions_dir(self, service_info):
        fmlogging.debug("Inside _generate_ebextensions_dir")
        if service_info:
            ebextension_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                        app_name=self.app_name)
            os.mkdir(ebextension_dir + "/.ebextensions")
            fp = open(ebextension_dir + "/.ebextensions/setup.config", "w")

            for serv in service_info:
                serv_handler = self.services[serv['service']['type']]
                setup_cfg = serv_handler.get_eb_extensions_contents()
                db_id = self.app_name + "-" + self.app_version
                db_name = constants.DEFAULT_DB_NAME
                user = constants.DEFAULT_DB_USER
                password = constants.DEFAULT_DB_PASSWORD
                setup_cfg = setup_cfg.format(db_id=db_id, db_name=db_name,
                                             user=user, password=password)

            fp.write(setup_cfg)
            fp.close()

    def _generate_platform_dockerfile_prev(self, service_ip_dict,
                                      service_info):
        fmlogging.debug("Inside _generate_platform_dockerfile")
        if service_info:
            app_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                      app_name=self.app_name)
            db_name = constants.DEFAULT_DB_NAME
            user = constants.DEFAULT_DB_USER
            password = constants.DEFAULT_DB_PASSWORD
            instance_dns = service_ip_dict[self.instance_name]

        # Generate runapp.sh
        runapp_fp = ''
        env_vars = ''
        export_vars = ''
        df_fp = ''

        if 'env_variables' in self.task_def.app_data or service_ip_dict:
            # Generate Dockerfile
            df_fp = open(self.instance_prov_workdir + "/Dockerfile.aws", "w")
            df = ("FROM ubuntu:14.04\n"
                  "RUN apt-get update && apt-get install -y \ \n"
                  "    python-setuptools python-pip git\n"
                  "ADD requirements.txt /src/requirements.txt \n"
                  "RUN cd /src; pip install -r requirements.txt \n"
                  "ADD . /src \n"
                  "EXPOSE 5000 \n"
                  )
            runapp_fp = open(self.instance_prov_workdir + "/runapp.sh", "w")
            runapp = ("#!/bin/sh \n")

            if service_ip_dict:
                print_prefix = "export "
                env_key_suffix = "="
                runapp_env_vars = utils.get_env_vars_string(self.task_def,
                                                            service_ip_dict,
                                                            self.app_variables,
                                                            self.services,
                                                            print_prefix,
                                                            env_key_suffix)
                runapp = runapp + runapp_env_vars
                print_prefix = "ENV "
                env_key_suffix = " "
                df_env_vars = utils.get_env_vars_string(self.task_def,
                                                        service_ip_dict,
                                                        self.app_variables,
                                                        self.services,
                                                        print_prefix,
                                                        env_key_suffix)
                df = df + df_env_vars

            if 'env_variables' in self.task_def.app_data:
                env_var_obj = self.task_def.app_data['env_variables']
                if env_var_obj:
                    for key, value in env_var_obj.iteritems():
                        env_vars = env_vars + (" ENV {key} {value}\n").format(key=key, value=value)
                        export_vars = export_vars + ("export {key}={value}\n").format(key=key, value=value)
                    df = df + env_vars
                    runapp = runapp + export_vars

            runapp = runapp + ("python /src/{entry_point}\n").format(entry_point=self.entry_point + ".py")
            runapp_fp.write(runapp)
            runapp_fp.close()

            # Setting permission to 555
            permission = s.S_IRUSR | s.S_IRGRP | s.S_IROTH | s.S_IXUSR | s.S_IXGRP | s.S_IXOTH
            os.chmod(self.instance_prov_workdir + "/runapp.sh", permission)

            df = df + ("CMD /src/runapp.sh \n")
            df_fp.write(df)
            df_fp.close()

    def _generate_platform_dockerfile(self, service_ip_dict,
                                      service_info):
        fmlogging.debug("Inside _generate_platform_dockerfile")

        env_vars = ''
        export_vars = ''

        # Generate Dockerfile
        df_fp = open(self.instance_prov_workdir + "/Dockerfile.aws", "w")
        df = ("FROM amazon/aws-eb-python:3.4.2-onbuild-3.5.1\n"
              "RUN apt-get update && apt-get install -y \ \n"
              "    python-setuptools python-pip git\n"
              "ADD requirements.txt /src/requirements.txt \n"
              "RUN cd /src; pip install -r requirements.txt \n"
              "ADD . /src \n"
              "EXPOSE 8080 \n"
            )
        # Generate runapp.sh
        runapp_fp = open(self.instance_prov_workdir + "/runapp.sh", "w")
        runapp = ("#!/bin/sh \n")

        if 'env_variables' in self.task_def.app_data or service_ip_dict:
            if service_ip_dict:
                print_prefix = "export "
                env_key_suffix = "="
                runapp_env_vars = utils.get_env_vars_string(self.task_def,
                                                            service_ip_dict,
                                                            self.app_variables,
                                                            self.services,
                                                            print_prefix,
                                                            env_key_suffix)
                runapp = runapp + runapp_env_vars
                print_prefix = "ENV "
                env_key_suffix = " "
                df_env_vars = utils.get_env_vars_string(self.task_def,
                                                        service_ip_dict,
                                                        self.app_variables,
                                                        self.services,
                                                        print_prefix,
                                                        env_key_suffix)
                df = df + df_env_vars

            if 'env_variables' in self.task_def.app_data:
                env_var_obj = self.task_def.app_data['env_variables']
                if env_var_obj:
                    for key, value in env_var_obj.iteritems():
                        env_vars = env_vars + (" ENV {key} {value}\n").format(key=key, value=value)
                        export_vars = export_vars + ("export {key}={value}\n").format(key=key, value=value)
                    df = df + env_vars
                    runapp = runapp + export_vars

        runapp = runapp + ("python /src/{entry_point}\n").format(entry_point=self.entry_point + ".py")
        runapp_fp.write(runapp)
        runapp_fp.close()

        # Setting permission to 555
        permission = s.S_IRUSR | s.S_IRGRP | s.S_IROTH | s.S_IXUSR | s.S_IXGRP | s.S_IXOTH
        os.chmod(self.instance_prov_workdir + "/runapp.sh", permission)

        df = df + ("CMD /src/runapp.sh \n")
        df_fp.write(df)
        df_fp.close()

    def _generate_for_python_app(self, app_obj, service_ip_dict, service_info):

        app_deploy_dir = ("{app_dir}/{app_name}").format(app_dir=self.app_dir, 
                                                         app_name=self.app_name)

        # Copy aws-creds to the app directory
        cp_cmd = ("cp -r {aws_creds_path} {app_deploy_dir}/.").format(aws_creds_path=AWS_CREDS_PATH,
                                                                      app_deploy_dir=app_deploy_dir)
        
        fmlogging.debug("Copying aws-creds directory..")
        fmlogging.debug(cp_cmd)
        
        os.system(cp_cmd)
        
        env_name = app_obj.get_cont_name()

        if len(env_name) + 6 >=40:
            env_name = env_name[0:30]

        key_name = env_name + "-" + str(randint(0,9)) + "-" + str(randint(0,9)) + "-" + str(randint(0,9))
        env_name = cname = key_name

        fmlogging.debug("Environment name:%s" % env_name)
        fmlogging.debug("Key name:%s" % key_name)
        fmlogging.debug("CNAME:%s" % cname)

        # Save environment name
        #cwd = os.getcwd()
        #os.chdir(app_deploy_dir)
        fp = open(app_deploy_dir + "/env-name", "w")
        fp.write(env_name)
        fp.flush()
        fp.close()

        # Read security_group_id, if defined
        sec_group = ''
        if os.path.exists(app_deploy_dir + "/sec-group"):
            fps = open(app_deploy_dir + "/sec-group","r")
            sec_group = fps.readline()
            sec_group = sec_group.rstrip().lstrip()
            entrypt_cmd = ("ENTRYPOINT [\"eb\", \"create\", \"{env_name}\", \"-c\", "
                           "\"{cname}\", \"--vpc.securitygroups\", \"{sec_group}\", "
                           "\"--keyname\", \"{key_name}\", \"--timeout\", \"20\"]  \n").format(env_name=env_name,
                                                                                               cname=cname,
                                                                                               sec_group=sec_group,
                                                                                               key_name=key_name)
        else:
            entrypt_cmd = ("ENTRYPOINT [\"eb\", \"create\", \"{env_name}\", \"-c\", "
                           "\"{cname}\", \"--keyname\", \"{key_name}\", \"--timeout\", \"20\"]  \n").format(env_name=env_name,
                                                                                                            cname=cname,
                                                                                                            key_name=key_name)

        dockerfile_maneuver = ("RUN mv Dockerfile.deploy Dockerfile.bak \n"
                               "RUN mv Dockerfile.aws Dockerfile \n")
            
        fmlogging.debug("Entrypoint cmd:%s" % entrypt_cmd)
        fmlogging.debug("Dockerfile maneuver:%s" % dockerfile_maneuver)

        create_keypair_cmd = ("RUN aws ec2 create-key-pair --key-name "
                              "{key_name} --query 'KeyMaterial' --output text > {key_file}.pem\n").format(key_name=key_name,
                                                                                                          key_file=key_name)
        #os.chdir(cwd)
        # Generate Dockerfile
        df = self.docker_handler.get_dockerfile_snippet("aws")
        df = df + ("COPY . /src \n"
              "WORKDIR /src \n"
              "RUN cp -r aws-creds $HOME/.aws \n"
              "{dockerfile_maneuver}"
              "{create_keypair_cmd}"
              "{entrypt_cmd}"
            ).format(aws_creds_path=AWS_CREDS_PATH, dockerfile_maneuver=dockerfile_maneuver,
                     create_keypair_cmd=create_keypair_cmd, entrypt_cmd=entrypt_cmd)

        fmlogging.debug("App dir: %s" % self.app_dir)
        docker_file_dir = app_deploy_dir
        fmlogging.debug("Dockerfile dir:%s" % docker_file_dir)
        docker_file = open(docker_file_dir + "/Dockerfile.deploy", "w")
        docker_file.write(df)
        docker_file.close()

        self._generate_elasticbeanstalk_dir(service_info, env_name)

        # Note: We do no need to generate ebextensions as we are directly provisioning RDS instance
        # self._generate_ebextensions_dir(service_info)
        self._generate_platform_dockerfile(service_ip_dict, service_info)

    def generate_for_logs(self, info):
        fmlogging.debug("AWS generator called for getting app logs for app:%s" % info['app_name'])

        app_name = info['app_name']
        app_version = info['app_version']
        app_dir = (constants.APP_STORE_PATH + "/{app_name}/{app_version}/{app_name}").format(app_name=app_name,
                                                                                             app_version=app_version)
        #cwd = os.getcwd()
        #os.chdir(app_dir)

        def _generate_retrieve_log_script(app_dir):
            if not os.path.exists(app_dir + "/" + constants.RETRIEVE_LOG_PATH):
                fp = open(app_dir + "/" + constants.RETRIEVE_LOG_PATH, "w")
                file_content = ("#!/bin/bash \n "
                                "cont_id=`sudo docker ps | awk '{print $1}' | tail -1` \n"
                                "sudo docker cp $cont_id:/var/log/uwsgi/uwsgi.log . \n"
                                "sudo chown ec2-user uwsgi.log \n"
                                "sudo chgrp ec2-user uwsgi.log \n"
                                )
                fp.write(file_content)
                fp.flush()
                fp.close()

        def _generate_df_toget_ec2_instance_ip(app_dir):
            # Generate Dockerfile
            df = self.docker_handler.get_dockerfile_snippet("aws")
            df = df + ("COPY . /src \n"
                       "WORKDIR /src \n"
                       "RUN cp -r aws-creds $HOME/.aws \ \n"
                            " && aws ec2 describe-instances")
            fp = open(app_dir + "/Dockerfile.get-instance-ip", "w")
            fp.write(df)
            fp.flush()
            fp.close()

        def _generate_partial_df_to_retrieve_logs(app_dir, pem_file_name):
            # Generate Dockerfile
            df = self.docker_handler.get_dockerfile_snippet("aws")
            df = df + ("COPY . /src \n"
                       "WORKDIR /src \n"
                       "RUN cp -r aws-creds $HOME/.aws \ \n"
                       " && mkdir ~/.ssh \ \n"
                       " && cp /src/{pem_file_name}.pem ~/.ssh/. \ \n"
                       " && chmod 400 ~/.ssh/{pem_file_name}.pem \ \n"
                       ).format(pem_file_name=pem_file_name)
            fp = open(app_dir + "/Dockerfile.retrieve-logs", "w")
            fp.write(df)
            fp.flush()
            fp.close()

        _generate_retrieve_log_script(app_dir)
        _generate_df_toget_ec2_instance_ip(app_dir)

        #app_dir = os.getcwd()
        pem_file_name = utils.read_environment_name(app_dir)

        _generate_partial_df_to_retrieve_logs(app_dir, pem_file_name)

        #os.chdir(cwd)

    def generate_to_secure(self, info):
        fmlogging.debug("AWS generator called for securing service:%s" % info['service_name'])
        df = self.docker_handler.get_dockerfile_snippet("aws")

        work_dir = ''
        if info['service_name']:
            service_name = info['service_name']
            service_version = info['service_version']

            if not work_dir:
                work_dir = (constants.SERVICE_STORE_PATH + "/{service_name}/{service_version}/").format(service_name=service_name,
                                                                                                        service_version=service_version)
            if service_name:
                parts = service_name.split("-")
                if parts[0] == 'mysql':
                    mysql_handler = awsh.MySQLServiceHandler(self.task_def)
                    service_modify_cmd = mysql_handler.get_makesecure_cmd(info)

                    # Create Dockerfile to check rds delete status
                    df_status = df + ("COPY . /src \n"
                                      "WORKDIR /src \n"
                                      "RUN cp -r aws-creds $HOME/.aws \n"
                                      "{service_modify_cmd}\n").format(service_modify_cmd=service_modify_cmd)
                    docker_file_status = open(work_dir + "/Dockerfile.modify", "w")
                    docker_file_status.write(df_status)
                    docker_file_status.flush()
                    docker_file_status.close()

                    # Create Dockerfile to check rds delete status
                    status_check_cmd = mysql_handler.get_status_check_cmd(info)
                    df_status = df + ("COPY . /src \n"
                                      "WORKDIR /src \n"
                                      "RUN cp -r aws-creds $HOME/.aws \n"
                                      "{status_check_cmd}\n").format(status_check_cmd=status_check_cmd)
                    docker_file_status = open(work_dir + "/Dockerfile.status", "w")
                    docker_file_status.write(df_status)
                    docker_file_status.flush()
                    docker_file_status.close()



    def generate_for_delete(self, info):
        df = self.docker_handler.get_dockerfile_snippet("aws")
        service_terminate_cmd = ''
        eb_terminate_cmd = ''
        delete_keypair_cmd = ''
        work_dir = ''
        if info['app_name']:
            fmlogging.debug("AWS generator called for delete for app:%s" % info['app_name'])

            app_name = info['app_name']
            app_version = info['app_version']
            work_dir = (constants.APP_STORE_PATH + "/{app_name}/{app_version}/{app_name}").format(app_name=app_name,
                                                                                                  app_version=app_version)
            fmlogging.debug("Dockerfile dir:%s" % work_dir)

            env_name = utils.read_environment_name(work_dir)

            delete_keypair_cmd = ("RUN aws ec2 delete-key-pair --key-name {env_name}").format(env_name=env_name)
            eb_terminate_cmd = ("RUN eb terminate {env_name} --force").format(env_name=env_name)

        if info['service_name']:
            service_name = info['service_name']
            service_version = info['service_version']

            if not work_dir:
                work_dir = (constants.SERVICE_STORE_PATH + "/{service_name}/{service_version}/").format(service_name=service_name,
                                                                                                        service_version=service_version)
            if service_name:
                parts = service_name.split("-")
                if parts[0] == 'mysql':
                    mysql_handler = awsh.MySQLServiceHandler(self.task_def)
                    service_terminate_cmd = mysql_handler.get_terminate_cmd(info)

                    # Create Dockerfile to check rds delete status
                    status_check_cmd = mysql_handler.get_status_check_cmd(info)
                    df_status = df + ("COPY . /src \n"
                                      "WORKDIR /src \n"
                                      "RUN cp -r aws-creds $HOME/.aws \n"
                                      "{status_check_cmd}\n").format(status_check_cmd=status_check_cmd)
                    docker_file_status = open(work_dir + "/Dockerfile.status", "w")
                    docker_file_status.write(df_status)
                    docker_file_status.flush()
                    docker_file_status.close()

                    # Create Dockerfile to delete security_group
                    delete_sec_group = mysql_handler.get_sec_group_delete_cmd(info)
                    df_sec_group = df + ("COPY . /src \n"
                                         "WORKDIR /src \n"
                                         "RUN cp -r aws-creds $HOME/.aws \n"
                                         "{delete_sec_group}\n").format(delete_sec_group=delete_sec_group)
                    docker_file_sec_group = open(work_dir + "/Dockerfile.secgroup", "w")
                    docker_file_sec_group.write(df_sec_group)
                    docker_file_sec_group.flush()
                    docker_file_sec_group.close()

        # Create Dockerfile to delete rds instance and terminate application
        df_delete = df + ("COPY . /src \n"
                          "WORKDIR /src \n"
                          "RUN cp -r aws-creds $HOME/.aws \n"
                          "{delete_keypair_cmd}\n"
                          "{eb_terminate_cmd}\n"
                          "{service_terminate_cmd}"
                          ).format(delete_keypair_cmd=delete_keypair_cmd,
                                   eb_terminate_cmd=eb_terminate_cmd,
                                   service_terminate_cmd=service_terminate_cmd)


        docker_file_delete = open(work_dir + "/Dockerfile.delete", "w")
        docker_file_delete.write(df_delete)
        docker_file_delete.flush()
        docker_file_delete.close()

    def generate(self, generate_type, service_ip_dict, service_info):
        if generate_type == 'service':
            fmlogging.debug("AWS generator called for service")
            self.service_obj = service.Service(self.task_def.service_data[0])
            # deploy_dir = self.service_obj.get_service_prov_work_location()
            # Copy aws-creds to the service deploy directory
            cp_cmd = ("cp -r {aws_creds_path} {deploy_dir}/.").format(aws_creds_path=AWS_CREDS_PATH,
                                                                      deploy_dir=self.deploy_dir)
        
            fmlogging.debug("Copying aws-creds directory..")
            fmlogging.debug(cp_cmd)
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
            fmlogging.debug("AWS generator called for app %s" %
                          self.task_def.app_data['app_name'])

            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status("GENERATING AWS ARTIFACTS")

            if self.app_type == 'python':
                self._generate_for_python_app(app_obj, service_ip_dict, service_info)
            else:
                print("Application of type %s not supported." % self.app_type)
        return 0