'''
Created on Jan 5, 2017

@author: devdatta
'''
import logging
import os
import stat
import subprocess
import time

from common import docker_lib
from common import service
from common import utils
from common import constants

RDS_INSTANCE_DEPLOY_DFILE = "Dockerfile.rds-instance-deploy"
RDS_INSTANCE_STAT_CHECK_DFILE = "Dockerfile.rds-instance-check"
MAX_WAIT_COUNT = 600

class MySQLServiceHandler(object):

    def __init__(self, task_def):
        self.task_def = task_def
        self.instance_name = ''
        self.instance_version = ''
        self.instance_prov_workdir = ''
        self.connection_name = ''
        self.database_version = ''
        self.database_tier = ''
        self.instance_ip_address = ''
        self.deploy_dir = ''
        self.app_status_file = ''
        
        # Set values using service_data first
        if task_def.service_data:
            self.service_obj = service.Service(task_def.service_data[0])
            self.instance_prov_workdir = self.service_obj.get_service_prov_work_location()
            self.instance_name = self.service_obj.get_service_name()
            self.instance_version = self.service_obj.get_service_version()

        # If app_data is present overwrite the previously set values
        if task_def.app_data:
            self.instance_prov_workdir = task_def.app_data['app_location'] + "/" + task_def.app_data['app_name']
            self.instance_name = task_def.app_data['app_name']
            self.instance_version = task_def.app_data['app_version']
            self.app_status_file = constants.APP_STORE_PATH + "/" + self.instance_name + "/" + self.instance_version + "/app-status.txt"

        self.deploy_dir = self.instance_prov_workdir

        self.docker_handler = docker_lib.DockerLib()

        # db_info contains the map of app_variables and their values
        self.db_info = {}

        # These are app_variables: user, password, db
        self.db_info['user'] = constants.DEFAULT_DB_USER
        self.db_info['password'] = constants.DEFAULT_DB_PASSWORD
        self.db_info['db'] = constants.DEFAULT_DB_NAME
            
    def _generate_rds_instance_create_df(self):
        logging.debug("Generating Dockerfile for RDS instance creation")
        db_name = constants.DEFAULT_DB_NAME
        db_id = self.instance_name + "-" + self.instance_version
        user = constants.DEFAULT_DB_USER
        password = constants.DEFAULT_DB_PASSWORD
        sec_group = ("`aws ec2 create-security-group --group-name {gname} --description \"My security group - SQL\"`").format(gname=db_id)
        add_rule = ("aws ec2 authorize-security-group-ingress --group-name {gname} --protocol tcp --port 3306 --cidr 0.0.0.0/0").format(gname=db_id)
        create_instance = ("aws rds create-db-instance --db-name {db_name}"
                           " --db-instance-identifier {db_id} --engine MySQL "
                           " --db-instance-class db.m1.medium --master-username {user} " 
                           " --master-user-password {password} --allocated-storage 10 "
                           " --vpc-security-group-ids $sec_group_1 --publicly-accessible").format(db_name=db_name,
                                                                                                  db_id=db_id,
                                                                                                  user=user,
                                                                                                  password=password)
        df = self.docker_handler.get_dockerfile_snippet("aws")
        df = df + ("COPY . /src \n"
              "WORKDIR /src \n"
              "RUN cp -r aws-creds $HOME/.aws \n"
              "RUN sec_group={sec_group} \ \n"
              "    && sec_group_1=`echo $sec_group | sed 's/{{//' | sed 's/}}//' | awk '{{print $2}}' | sed 's/\"//'g` \ \n"
              "    && {add_rule} \ \n"
              "    && {create_instance}").format(sec_group=sec_group,
                                              add_rule=add_rule,
                                              create_instance=create_instance)
              
        fp = open(self.deploy_dir + "/" + RDS_INSTANCE_DEPLOY_DFILE, "w")
        fp.write(df)
        fp.close()

    def _generate_rds_instance_check_df(self):
        logging.debug("Generating Dockerfile for RDS instance checking")
        db_id = self.instance_name + "-" + self.instance_version
        
        entry_pt = ("ENTRYPOINT [\"aws\", \"rds\", \"describe-db-instances\", "
                    " \"--db-instance-identifier\", \"{db_id}\"]").format(db_id=db_id)
        df = self.docker_handler.get_dockerfile_snippet("aws")
        df = df + ("COPY . /src \n"
              "WORKDIR /src \n"
              "RUN cp -r aws-creds $HOME/.aws \n"
              "{entry_pt}").format(entry_pt=entry_pt)
              
        fp = open(self.deploy_dir + "/" + RDS_INSTANCE_STAT_CHECK_DFILE, "w")
        fp.write(df)
        fp.close()

    def _build_containers(self):
        logging.debug("Building RDS instance provisioning containers")
        cwd = os.getcwd()
        os.chdir(self.deploy_dir)
        
        cont_name = self.instance_name + "--" + self.instance_version + "--deploy-rds" 
        self.docker_handler.build_container_image(cont_name, RDS_INSTANCE_DEPLOY_DFILE)
        
        cont_name = self.instance_name + "--" + self.instance_version + "--check-rds" 
        self.docker_handler.build_container_image(cont_name, RDS_INSTANCE_STAT_CHECK_DFILE)
        
        os.chdir(cwd)

    def _generate_docker_files(self):
        self._generate_rds_instance_create_df()
        self._generate_rds_instance_check_df()

    def _get_rds_instance_dns(self):
        cont_name = self.instance_name + "--" + self.instance_version + "--check-rds"
        cmd = ("docker run {cont_name}").format(cont_name=cont_name)

        time_out = False
        count = 0
        instance_available = False
        while not time_out:
            try:
                output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, shell=True).communicate()[0]
                logging.debug("Output:%s" % output)
                lines = output.split("\n")
                print(output)
                for line in lines:
                    if line.find("DBInstanceStatus") >= 0:
                        parts = line.split(":")
                        status = parts[1].rstrip().lstrip().replace("\"", "").replace(",", "")
                        if status == 'available':
                            instance_available = True
                    if instance_available:
                        if line.find("Address") >= 0:
                            parts = line.split(":")
                            instance_dns = parts[1].rstrip().lstrip().replace("\"", "")
                            return instance_dns
            except Exception as e:
                print(e)
            count = count + 1
            
            self.docker_handler.stop_container(cont_name,
                                               "Stopping container created for checking instance prov status")
            self.docker_handler.remove_container(cont_name,
                                                 "Stopping container created for checking instance prov status")
            if count == MAX_WAIT_COUNT:
                time_out = True
            else:
                time.sleep(2)
        return

    def _save_instance_information(self, instance_ip):
        fp = open(self.service_obj.get_service_details_file_location(), "w")
        fp.write("%s::%s\n" % (constants.DB_NAME, constants.DEFAULT_DB_NAME))
        fp.write("%s::%s\n" % (constants.DB_USER, constants.DEFAULT_DB_USER))
        fp.write("%s::%s\n" % (constants.DB_USER_PASSWORD, constants.DEFAULT_DB_PASSWORD))
        fp.close()

        if self.app_status_file:
            fp = open(self.app_status_file, "a")
            fp.write("%s::%s, " % (constants.RDS_INSTANCE, instance_ip))
            fp.write("%s::%s, " % (constants.DB_NAME, constants.DEFAULT_DB_NAME))
            fp.write("%s::%s, " % (constants.DB_USER, constants.DEFAULT_DB_USER))
            fp.write("%s::%s, " % (constants.DB_USER_PASSWORD, constants.DEFAULT_DB_PASSWORD))
            fp.close()

    def get_terminate_cmd(self, delete_info):
        app_name = delete_info['app_name']
        app_version = delete_info['app_version']

        instance_name = ("{app_name}-{app_version}").format(app_name=app_name,
                                                            app_version=app_version)
        rds_delete_cmd = ("RUN aws rds delete-db-instance ")
        rds_delete_cmd = rds_delete_cmd + ("--db-instance-identifier {instance_name} ")
        rds_delete_cmd = rds_delete_cmd + ("--skip-final-snapshot").format(instance_name=instance_name)

        return rds_delete_cmd

    def get_eb_extensions_contents(self):
        # TODO(devkulkarni): Below setup_cfg is for DynamoDB.
        # We want one for RDS
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

        setup_cfg = ("Resources:\n"
                     "  RDSInstance:\n"
                     "    Type: AWS::RDS::DBInstance\n"
                     "    Properties:\n"
                     "      DBInstanceIdentifer: {db_id}\n"
                     "      DBName: {db_name}\n"
                     "      Engine: MySQL\n"
                     "      DBInstanceClass: db.m1.medium\n"
                     "      MasterUsername: {user}\n"
                     "      MasterUserPassword: {password}\n"
                     "      AllocatedStorage: 10\n"
                     )

        return setup_cfg

    def generate_instance_artifacts(self):
        self._generate_docker_files()

    def get_instance_info(self):
        return self.db_info

    def build_instance_artifacts(self):
        self._build_containers()
        
    def provision_and_setup(self):
        instance_dns = self._get_rds_instance_dns()
        logging.debug("RDS instance DNS:%s" % instance_dns)
        self._save_instance_information(instance_dns)
        return instance_dns
        
