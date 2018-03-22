import logging
import os
import subprocess
import time

from common import docker_lib
from common import service
from common import constants
from common import utils
from common import fm_logger

RDS_INSTANCE_DEPLOY_DFILE = "Dockerfile.rds-instance-deploy"
RDS_INSTANCE_STAT_CHECK_DFILE = "Dockerfile.rds-instance-check"
MAX_WAIT_COUNT = 600

fmlogging = fm_logger.Logging()

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
        self.db_info['db'] = constants.DEFAULT_DB_NAME

        # Check if we have already provisioned a db instance. If so, use that password
        password = self._read_password()
        if not password:
            self.db_info['password'] = utils.generate_aws_password()
        else:
            self.db_info['password'] = password

    def _read_password(self):
        password = ''
        path = ''
        if hasattr(self, 'service_obj'):
            path = self.service_obj.get_service_details_file_location()
        if path and os.path.exists(path):
            password = utils.read_password(path)
        return password

    def _get_cidr_block(self):
        df = self.docker_handler.get_dockerfile_snippet("aws")
        df = df + ("COPY . /src \n"
              "WORKDIR /src \n"
              "RUN cp -r aws-creds $HOME/.aws \n"
              "RUN aws ec2 describe-vpcs")
        fp = open(self.deploy_dir + "/Dockerfile.get-cidrblock", "w")
        fp.write(df)
        fp.close()

        #cwd = os.getcwd()
        #os.chdir(self.deploy_dir)
        df_loc = self.deploy_dir
        cont_name = self.instance_name + "-cidrblock"
        err, output = self.docker_handler.build_ct_image(cont_name, df_loc + "/Dockerfile.get-cidrblock", df_context=df_loc)

        cidrblock = ''
        for line in output.split("\n"):
            if line.find("CidrBlock") >= 0:
                parts = line.split(":")
                cidrblock = parts[1].replace('"','').replace(',','').rstrip().lstrip()
            if line.find("IsDefault") >= 0:
                parts = line.split(":")
                if parts[1].lower() == 'true':
                    break

        self.docker_handler.remove_container_image(cont_name, "Done getting cidr block")
        fmlogging.debug("CIDR Block:%s" % cidrblock)
        #os.chdir(cwd)
        return cidrblock

    def _get_security_group_id(self):
        df = self.docker_handler.get_dockerfile_snippet("aws")
        db_id = self.instance_name + "-" + self.instance_version
        sec_group = ("RUN aws ec2 create-security-group --group-name {gname} --description {desc}").format(gname=db_id,
                                                                                                           desc=db_id)
        df = df + ("COPY . /src \n"
              "WORKDIR /src \n"
              "RUN cp -r aws-creds $HOME/.aws \n"
              "{sec_group}").format(sec_group=sec_group)
        fp = open(self.deploy_dir + "/Dockerfile.security-group", "w")
        fp.write(df)
        fp.close()

        #cwd = os.getcwd()
        #os.chdir(self.deploy_dir)
        df_loc = self.deploy_dir
        cont_name = self.instance_name + "-security-group"
        err, output = self.docker_handler.build_ct_image(cont_name, df_loc + "/Dockerfile.security-group", df_context=df_loc)
        secgroup_id = ''
        for line in output.split("\n"):
            if line.find("GroupId") >= 0:
                parts = line.split(":")
                secgroup_id = parts[1].replace('"','').rstrip().lstrip()
                break
        # Save secgroup_id
        fp = open("sec-group", "w")
        fp.write(secgroup_id)
        fp.flush()
        fp.close()
        #os.chdir(cwd)
        self.docker_handler.remove_container_image(cont_name, "Done getting security_group id")
        return secgroup_id

    def _generate_rds_instance_create_df(self):
        fmlogging.debug("Generating Dockerfile for RDS instance creation")
        db_name = constants.DEFAULT_DB_NAME
        db_id = self.instance_name + "-" + self.instance_version
        user = constants.DEFAULT_DB_USER
        password = self.db_info['password']

        df = self.docker_handler.get_dockerfile_snippet("aws")
        df = df + ("COPY . /src \n"
              "WORKDIR /src \n"
              "RUN cp -r aws-creds $HOME/.aws \ \n")

        add_rule = ''
        sec_group_id = self._get_security_group_id()
        cidrblock = ''
        create_instance = ''
        if self.task_def.service_data[0]['lock'] == 'true':
            cidrblock = self._get_cidr_block()
            add_rule = ("aws ec2 authorize-security-group-ingress --group-name {gname} --protocol tcp --port 3306 --cidr {cidrblock}").format(gname=db_id,
                                                                                                                                              cidrblock=cidrblock)
            create_instance = ("aws rds create-db-instance --db-name {db_name}"
                               " --db-instance-identifier {db_id} --engine MySQL "
                               " --db-instance-class db.t2.micro --master-username {user} "
                               " --master-user-password '{password}' --allocated-storage 10 "
                               " --vpc-security-group-ids {sec_group_id}").format(db_name=db_name,
                                                                                  db_id=db_id,
                                                                                  user=user,
                                                                                  password=password,
                                                                                  sec_group_id=sec_group_id)
            df = df + ("    &&  {add_rule} \ \n"
                       "    && {create_instance}").format(add_rule=add_rule, create_instance=create_instance)
        else:
            cidrblock = '0.0.0.0/0'
            add_rule = ("aws ec2 authorize-security-group-ingress --group-name {gname} --protocol tcp --port 3306 --cidr {cidrblock}").format(gname=db_id,
                                                                                                                                              cidrblock=cidrblock)
            create_instance = ("aws rds create-db-instance --db-name {db_name}"
                               " --db-instance-identifier {db_id} --engine MySQL "
                               " --db-instance-class db.t2.micro --master-username {user} "
                               " --master-user-password '{password}' --allocated-storage 10 "
                               " --vpc-security-group-ids {sec_group_id} --publicly-accessible").format(db_name=db_name,
                                                                                                        db_id=db_id,
                                                                                                        user=user,
                                                                                                        password=password,
                                                                                                        sec_group_id=sec_group_id)
            df = df + ("    &&  {add_rule} \ \n"
                       "    && {create_instance}").format(add_rule=add_rule, create_instance=create_instance)
            #df = df + ("    && {create_instance}").format(create_instance=create_instance)

        fp = open(self.deploy_dir + "/" + RDS_INSTANCE_DEPLOY_DFILE, "w")
        fp.write(df)
        fp.close()

        # Save db creds
        fp = open(self.service_obj.get_service_details_file_location(), "w")
        fp.write("%s::%s\n" % (constants.DB_NAME, constants.DEFAULT_DB_NAME))
        fp.write("%s::%s\n" % (constants.DB_USER, constants.DEFAULT_DB_USER))
        fp.write("%s::%s\n" % (constants.DB_USER_PASSWORD, self.db_info['password']))
        fp.close()

    def _generate_rds_instance_check_df(self):
        fmlogging.debug("Generating Dockerfile for RDS instance checking")
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
        fmlogging.debug("Building RDS instance provisioning containers")
        #cwd = os.getcwd()
        #os.chdir(self.deploy_dir)
        deploy_dir = self.deploy_dir
        cont_name = self.instance_name + "--" + self.instance_version + "--deploy-rds" 
        self.docker_handler.build_container_image(cont_name, deploy_dir + "/" + RDS_INSTANCE_DEPLOY_DFILE,
                                                  df_context=deploy_dir)
        
        cont_name = self.instance_name + "--" + self.instance_version + "--check-rds" 
        self.docker_handler.build_container_image(cont_name, deploy_dir + "/" + RDS_INSTANCE_STAT_CHECK_DFILE,
                                                  df_context=deploy_dir)
        
        #os.chdir(cwd)

    def _generate_docker_files(self):
        self._generate_rds_instance_create_df()
        self._generate_rds_instance_check_df()

    def _get_rds_instance_dns(self):
        cont_name = self.instance_name + "--" + self.instance_version + "--check-rds"
        cmd = ("docker run {cont_name}").format(cont_name=cont_name)

        time_out = False
        count = 0
        instance_available = False
        instance_dns = ''

        def _cleanup_containers(cont_name):
            message = ("Stopping container %s" % cont_name)
            self.docker_handler.stop_container(cont_name, message)
            self.docker_handler.remove_container(cont_name, message)

        while not time_out:
            try:
                output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, shell=True).communicate()[0]
                fmlogging.debug("Output:%s" % output)
                lines = output.split("\n")
                print(output)
                for line in lines:
                    if line.find("DBInstanceStatus") >= 0:
                        parts = line.split(":")
                        status = parts[1].rstrip().lstrip().replace("\"", "").replace(",", "")
                        if status == 'available':
                            instance_available = True
                    #instance_available = utils.check_if_available(line)
                    if instance_available:
                        if line.find("Address") >= 0:
                            parts = line.split(":")
                            instance_dns = parts[1].rstrip().lstrip().replace("\"", "")
                            _cleanup_containers(cont_name)
                            message = ("Removing container image: %s" % cont_name)
                            self.docker_handler.remove_container_image(cont_name, message)

                            cont_name = self.instance_name + "--" + self.instance_version + "--deploy-rds"
                            _cleanup_containers(cont_name)
                            message = ("Removing container image: %s" % cont_name)
                            self.docker_handler.remove_container_image(cont_name, message)
                            return instance_dns
            except Exception as e:
                print(e)
            count = count + 1

            _cleanup_containers(cont_name)

            if count == MAX_WAIT_COUNT:
                time_out = True
            else:
                time.sleep(2)
        return instance_dns

    def _save_instance_information(self, instance_ip):

        if self.app_status_file:
            fp = open(self.app_status_file, "a")
            fp.write("%s::%s, " % (constants.RDS_INSTANCE, instance_ip))
            fp.write("%s::%s, " % (constants.DB_NAME, constants.DEFAULT_DB_NAME))
            fp.write("%s::%s, " % (constants.DB_USER, constants.DEFAULT_DB_USER))
            fp.write("%s::%s, " % (constants.DB_USER_PASSWORD, self._read_password()))
            fp.close()

    def _get_instance_name(self, delete_info):
        if delete_info['app_name']:
            app_name = delete_info['app_name']
            app_version = delete_info['app_version']
            instance_name = ("{app_name}-{app_version}").format(app_name=app_name,
                                                                app_version=app_version)
        elif delete_info['service_name']:
            service_name = delete_info['service_name']
            service_version = delete_info['service_version']

            instance_name = ("{service_name}-{service_version}").format(service_name=service_name,
                                                                        service_version=service_version)
        return instance_name

    def get_terminate_cmd(self, delete_info):
        instance_name = self._get_instance_name(delete_info)
        rds_delete_cmd = ("RUN aws rds delete-db-instance ")
        rds_delete_cmd = rds_delete_cmd + ("--db-instance-identifier {instance_name} ").format(instance_name=instance_name)
        rds_delete_cmd = rds_delete_cmd + ("--skip-final-snapshot")
        return rds_delete_cmd

    def get_makesecure_cmd(self, delete_info):
        instance_name = self._get_instance_name(delete_info)
        rds_modify_cmd = ("RUN aws rds modify-db-instance ")
        rds_modify_cmd = rds_modify_cmd + ("--db-instance-identifier {instance_name} ").format(instance_name=instance_name)
        rds_modify_cmd = rds_modify_cmd + ("--no-publicly-accessible")
        return rds_modify_cmd

    def get_sec_group_delete_cmd(self, delete_info):
        instance_name = self._get_instance_name(delete_info)
        delete_secgroup_cmd = ("RUN aws ec2 delete-security-group --group-name {instance_name}\n").format(instance_name=instance_name)
        return delete_secgroup_cmd

    def get_status_check_cmd(self, delete_info):
        instance_name = self._get_instance_name(delete_info)
        check_cmd = ("ENTRYPOINT [\"aws\", \"rds\", \"describe-db-instances\", \"--db-instance-identifier\", \"{instance_name}\"] \n").format(instance_name=instance_name)
        return check_cmd

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
                     "      DBInstanceClass: db.t2.micro\n"
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
        fmlogging.debug("RDS instance DNS:%s" % instance_dns)
        self._save_instance_information(instance_dns)
        return instance_dns
        
    def cleanup(self):
        # Stop and remove container generated for creating the database
        if self.task_def.service_data:

            cont_name = self.instance_name + "--" + self.instance_version + "--deploy-rds"
            self.docker_handler.stop_container(cont_name, "container created to deploy rds no longer needed.")
            self.docker_handler.remove_container(cont_name, "container created to deploy rds no longer needed.")
            self.docker_handler.remove_container_image(cont_name, "container created to deploy rds no longer needed.")

            cont_name = self.instance_name + "--" + self.instance_version + "--check-rds"
            self.docker_handler.stop_container(cont_name, "container created to deploy rds no longer needed.")
            self.docker_handler.remove_container(cont_name, "container created to deploy rds no longer needed.")
            self.docker_handler.remove_container_image(cont_name, "container created to deploy rds no longer needed.")
