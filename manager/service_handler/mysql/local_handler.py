import logging

import os
import sys
import subprocess

from docker import Client

from common import service
from common import constants

from manager.service_handler.mysql import helper

class MySQLServiceHandler(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')

        self.service_obj = service.Service(self.task_def.service_data[0])
        self.service_name = self.service_obj.get_service_name()
        self.mysql_db_name = constants.DEFAULT_DB_NAME
        self.mysql_user = constants.DEFAULT_DB_USER
        self.mysql_password = constants.DEFAULT_DB_PASSWORD
        self.mysql_root_password = constants.DEFAULT_DB_PASSWORD
        self.mysql_version = 'mysql:5.5'

        self.db_info = {}
        self.db_info['root_user'] = 'root'
        self.db_info['root_password'] = self.mysql_root_password

        self.db_info['user'] = self.mysql_user
        self.db_info['password'] = self.mysql_password
        self.db_info['db'] = self.mysql_db_name

        self.service_info = {}
        self.service_info['name'] = self.service_name
        self.service_info['version'] = self.service_obj.get_service_version()
        if self.service_obj.get_setup_file_content():
            self.db_info['setup_file'] = 'setup.sh'

        self.app_status_file = ''
        if self.task_def.app_data:
            self.app_name = self.task_def.app_data['app_name']
            self.app_status_file = constants.APP_STORE_PATH + "/" + self.app_name + "/" 
            self.app_status_file = self.app_status_file + self.service_obj.get_service_version() + "/app-status.txt"

    def _get_cont_name(self):
        if self.task_def.app_data:        
            app_name = self.task_def.app_data['app_name']
            app_loc = self.task_def.app_data['app_location']
            k = app_loc.rfind("/")
            app_loc = app_loc[k+1:]
            app_loc = app_loc.replace(":","-")
            cont_name = app_name + "-" + app_loc + "-mysql"
        else:
            serv_version = self.service_obj.get_service_version()
            cont_name = serv_version + "-mysql"
        return cont_name

    def _execute_cmd(self, cmd):
        err= ''
        output=''
        try:
            chanl = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, shell=True).communicate()
            err = chanl[1]
            output = chanl[0]
        except Exception as e:
            logging.error(e)
        return err, output

    def _run_container_with_env(self, cont_name, env_vars_dict):
        env_string = ""
        for key, value in env_vars_dict.iteritems():
            env_string = env_string + "-e " + '"' + key + '=' + value + '"' + " "
            logging.debug("Environment string %s" % env_string)

        """Run container asynchronously."""
        run_cmd = ("docker run {env_string} -i -d --publish-all=true {cont_name}").format(
            env_string=env_string,
            cont_name=cont_name)
        logging.debug("Docker run cmd:%s" % run_cmd)
        err, output = self._execute_cmd(run_cmd)
        return err, output

    def _deploy_service_container(self):             
        logging.debug("Deploying mysql container")
        #db_name = service_details['db_name']            
        env = {"MYSQL_ROOT_PASSWORD": self.mysql_root_password,
               "MYSQL_DATABASE": self.mysql_db_name,
               "MYSQL_USER": self.mysql_user,
               "MYSQL_PASSWORD": self.mysql_password}
        cont_name = self._get_cont_name()
                    
        self.docker_client.import_image(image=self.mysql_version)
        serv_cont = self.docker_client.create_container(self.mysql_version,
                                                        detach=True,
                                                        environment=env,
                                                        name=cont_name)
        self.docker_client.start(serv_cont)

        cont_data = self.docker_client.inspect_container(serv_cont)
        service_ip_addr = cont_data['NetworkSettings']['IPAddress']
        logging.debug("MySQL Service IP Address:%s" % service_ip_addr)

        self.db_info['host'] = service_ip_addr

        return service_ip_addr

    def _deploy_service_container_mac(self):
        logging.debug("Deploying mysql container")
        #db_name = service_details['db_name']                                                                      
        env = {"MYSQL_ROOT_PASSWORD": self.mysql_root_password,
               "MYSQL_DATABASE": self.mysql_db_name,
               "MYSQL_USER": self.mysql_user,
               "MYSQL_PASSWORD": self.mysql_password}
        cont_name = self._get_cont_name()

        err, cont_id = self._run_container_with_env(self.mysql_version, env)
        cont_id = cont_id.strip()

        port_cmd = ("docker inspect {cont_id} | grep HostPort | awk '{{print $2}}' | sed 's/\"//'g").format(cont_id=cont_id)

        err, service_port = self._execute_cmd(port_cmd)
        service_port = service_port.strip()

        service_ip_addr = ''
        if not err:
            #docker_host_fp = "."                                                                                  
            docker_host_fp = os.path.dirname(sys.modules[__name__].__file__)
            if os.path.exists(docker_host_fp + "/docker_host.txt"):
                fp = open(docker_host_fp + "/docker_host.txt", "r")
                line = fp.readline()
                parts = line.split("=")
                service_ip_addr=parts[1].strip() + ":" + service_port
            else:
                service_ip_addr='0.0.0.0' + ":" + service_port
            #service_ip_addr=parts[1].strip()
            self.db_info['host'] = service_ip_addr
            self.db_info['port'] = service_port

        return service_ip_addr
    
    def _setup_service_container(self):
        logging.debug("Setting up service container")
        work_dir = self.service_obj.get_service_prov_work_location()
        helper.setup_database(work_dir, self.db_info, self.service_info)

    def _save_instance_information(self, instance_ip):

        fp = open(self.service_obj.get_service_details_file_location(), "w")

        fp.write("%s::%s\n" % (constants.DB_NAME, constants.DEFAULT_DB_NAME))
        fp.write("%s::%s\n" % (constants.DB_USER, constants.DEFAULT_DB_USER))
        fp.write("%s::%s\n" % (constants.DB_USER_PASSWORD, constants.DEFAULT_DB_PASSWORD))
        fp.write("%s::%s\n" % (constants.DB_ROOT_PASSWORD, self.mysql_root_password))
        fp.write("%s::%s\n" % (constants.MYSQL_VERSION, self.mysql_version))
        fp.close()

        if self.app_status_file:
            fp = open(self.app_status_file, "a")
            fp.write("%s::%s, " % (constants.SQL_CONTAINER, instance_ip))
            fp.write("%s::%s, " % (constants.DB_NAME, constants.DEFAULT_DB_NAME))
            fp.write("%s::%s, " % (constants.DB_USER, constants.DEFAULT_DB_USER))
            fp.write("%s::%s, " % (constants.DB_USER_PASSWORD, constants.DEFAULT_DB_PASSWORD))
            fp.close()

    # Public interface
    def provision_and_setup(self):
        service_ip = ''
        import platform
        if platform.system() == 'Darwin':
            service_ip = self._deploy_service_container_mac()
        else:
            service_ip = self._deploy_service_container()

        self._setup_service_container()
        self._save_instance_information(service_ip)
        return service_ip
    
    def cleanup(self):
        pass

    def get_instance_info(self):
        return self.db_info

    @classmethod
    def get_instance_name(self, info):
        if info['app_name']:
            app_name = info['app_name']
            app_version = info['app_version']
            instance_name = app_name + "-" + app_version + "-mysql"
        if info['service_name']:
            instance_name = info['service_name']
        return instance_name
