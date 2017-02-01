'''
Created on Dec 6, 2016

@author: devdatta
'''
import logging
import subprocess
import time

from docker import Client
from common import app
from common import service
from common import utils
from common import docker_lib
from common import constants

from manager.service_handler.mysql import aws_handler as awsh

TMP_LOG_FILE = "/tmp/lme-aws-deploy-output.txt"

class AWSDeployer(object):

    def __init__(self, task_def):
        self.task_def = task_def
        self.logger = logging.getLogger(name=self.__class__.__name__)

        self.services = {}
        self.app_obj = ''

        if self.task_def.app_data:
            self.app_obj = app.App(self.task_def.app_data)

        if task_def.service_data:
            self.service_obj = service.Service(task_def.service_data[0])
            if self.service_obj.get_service_type() == 'mysql':
                self.services['mysql'] = awsh.MySQLServiceHandler(self.task_def)

        self.docker_handler = docker_lib.DockerLib()

        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')

    def _parse_container_id(self, app_cont_name):
        cont_grep_cmd = ("docker ps -a | grep {cont_name} | cut -d ' ' -f 1 ").format(cont_name=app_cont_name)
        logging.debug("Container grep command:%s" % cont_grep_cmd)
        cont_id = subprocess.check_output(cont_grep_cmd, shell=True)
        logging.debug("Container id:%s" % cont_id)
        return cont_id

    def _process_logs(self, cont_id, app_cont_name, app_obj):

        logging.debug("Fetching logs from AWS deployer container")
        logged_status = []

        docker_logs_cmd = ("docker logs {cont_id}").format(cont_id=cont_id)
        logging.debug("Docker logs command:%s" % docker_logs_cmd)
        cname = "1.2.3.4"

        is_env_ok = False
        logging.debug("Parsing statuses from AWS")
        while not is_env_ok:
            log_lines = subprocess.check_output(docker_logs_cmd, shell=True)
            log_lines = log_lines.split("\n")
            for line in log_lines:
                line = line.rstrip().lstrip()
                if line.find("CNAME:") >= 0:
                    stat = line.split(":")
                    cname = stat[1].rstrip().lstrip()
                if line.find("ERROR:") >= 0:
                    stat = line.split(":")
                    error = stat[1].rstrip().lstrip()
                    if error not in logged_status:
                        logged_status.append(error)
                        app_obj.update_app_status(error)
                if line.find("INFO:") >= 0:
                    stat = line.split(":")
                    status = stat[1]
                    if status not in logged_status:
                        logged_status.append(status)
                        a = line.find("INFO:")
                        line = line[a+5:]
                        app_obj.update_app_status(line)
                    if status.lower().find("successfully launched environment") >= 0:
                        is_env_ok = True
            time.sleep(1)

        return cname
        
    def _deploy_app_container(self, app_obj):
        app_cont_name = app_obj.get_cont_name()
        
        logging.debug("Deploying app container:%s" % app_cont_name)

        docker_run_cmd = ("docker run -i -t -d {app_container}").format(app_container=app_cont_name)
        cont_id = subprocess.check_output(docker_run_cmd, shell=True)
        logging.debug("Running container id:%s" % cont_id)

        cname = self._process_logs(cont_id, app_cont_name, app_obj)
        return cname

    def _cleanup(self, app_obj):
        # Remove any temporary container created for service provisioning
        for serv in self.task_def.service_data:
            serv_handler = self.services[serv['service']['type']]
            serv_handler.cleanup()

        # Remove app container
        self.docker_handler.stop_container(app_obj.get_cont_name(),
                                           "container created to deploy application no longer needed.")
        self.docker_handler.remove_container(app_obj.get_cont_name(),
                                             "container created to deploy application no longer needed.")
        self.docker_handler.remove_container_image(app_obj.get_cont_name(),
                                                   "container created to deploy application no longer needed.")

    def deploy_for_delete(self, info):
        logging.debug("AWS deployer for called to delete app:%s" % info['app_name'])
        app_name = info['app_name']
        app_version = info['app_version']
        dep_id = info['dep_id']
        utils.remove_artifact(dep_id, constants.APP_STORE_PATH, "app_ids.txt", app_name, app_version)

        # Remove service directories as well, if a service has been provisioned
        service_name = info['service_name']
        service_version = info['service_version']
        service_id = info['service_id']

        if service_name:
            utils.remove_artifact(service_id, constants.SERVICE_STORE_PATH,
                                  "service_ids.txt", service_name, service_version)

    def deploy(self, deploy_type, deploy_name):
        if deploy_type == 'service':
            logging.debug("AWS deployer called for deploying RDS instance")

            service_ip_list = []
            for serv in self.task_def.service_data:
                serv_handler = self.services[serv['service']['type']]
                # Invoke public interface
                utils.update_status(self.service_obj.get_status_file_location(),
                                    constants.DEPLOYING_SERVICE_INSTANCE)
                if self.app_obj:
                    self.app_obj.update_app_status(constants.DEPLOYING_SERVICE_INSTANCE)
                service_ip = serv_handler.provision_and_setup()
                service_ip_list.append(service_ip)
                utils.update_status(self.service_obj.get_status_file_location(),
                                    constants.SERVICE_INSTANCE_DEPLOYMENT_COMPLETE)
                if self.app_obj:
                    self.app_obj.update_app_status(constants.SERVICE_INSTANCE_DEPLOYMENT_COMPLETE)
                utils.save_service_instance_ip(self.service_obj.get_status_file_location(),
                                               service_ip)

            # TODO(devkulkarni): Add support for returning multiple service IPs
            return service_ip_list[0]
        else:
            logging.debug("AWS deployer called for app %s" %
                          self.task_def.app_data['app_name'])
            app_obj = app.App(self.task_def.app_data)
            app_obj.update_app_status(constants.DEPLOYING_APP)
            app_ip_addr = self._deploy_app_container(app_obj)
            app_obj.update_app_status(constants.APP_DEPLOYMENT_COMPLETE)
            app_obj.update_app_ip(app_ip_addr)
            self.logger.debug("AWS deployment complete.")
            self.logger.debug("Removing temporary containers created to assist in the deployment.")
            self._cleanup(app_obj)
