'''
Created on Oct 26, 2016

@author: devdatta
'''
from docker import Client
from common import app

class LocalDeployer(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.18')
        
    def _deploy_service_container(self, service_name):
        
        def _deploy_mysql_container(service_details):            
            def _get_cont_name():                
                app_name = self.task_def.app_data['app_name']
                app_loc = self.task_def.app_data['app_location']
                k = app_loc.rfind("/")
                app_loc = app_loc[k+1:]
                app_loc = app_loc.replace(":","-")
                cont_name = app_name + "-" + app_loc + "-mysql"                
                return cont_name
            
            print("Deploy mysql container")
            db_name = service_details['db_name']            
            env = {"MYSQL_ROOT_PASSWORD": "lmeuserpass",
                   "MYSQL_DATABASE": db_name,
                   "MYSQL_USER": "lmeuser",
                   "MYSQL_PASSWORD": "lmeuserpass"}
            cont_name = _get_cont_name()
                        
            self.docker_client.import_image(image="mysql:5.5")
            serv_cont = self.docker_client.create_container('mysql:5.5', detach=True, environment=env, name=cont_name)
            self.docker_client.start(serv_cont)
            cont_data = self.docker_client.inspect_container(serv_cont)
            service_ip_addr = cont_data['NetworkSettings']['IPAddress']
            print("Service IP Address:%s" % service_ip_addr)
            return service_ip_addr
        
        services = self.task_def.service_data
        service_to_deploy = ''
        for serv in services:
            if serv['service_name'] == service_name:
                service_to_deploy = serv
                break
        
        if service_to_deploy['service_type'] == 'mysql':
            serv_ip_addr = _deploy_mysql_container(service_to_deploy['service_details'])
        else:
            print("Deployment of service %s not supported currently." % service_to_deploy['service_type'])

        return serv_ip_addr
    
    def _deploy_app_container(self):

        app_obj = app.App(self.task_def.app_data)
        app_cont_name = app_obj.get_cont_name()
        self.docker_client.import_image(image=app_cont_name)
        port_list = []
        port_list.append(5000)
        host_cfg = self.docker_client.create_host_config(publish_all_ports=True)
        app_cont = self.docker_client.create_container(app_cont_name, detach=True,
                                                       ports=port_list, name=app_cont_name,
                                                       host_config=host_cfg)
        self.docker_client.start(app_cont)
        
        cont_data = self.docker_client.inspect_container(app_cont)
        
        app_ip_addr = cont_data['NetworkSettings']['IPAddress']
        
        # get host port
        # app_port_list = cont_data['NetworkSettings']['Ports']
        # port_list = app_port_list["5000/tcp"]
        # app_host_port = port_list[0]["HostPort"]
        
        app_url = ("{app_ip_addr}:{app_port}").format(app_ip_addr=app_ip_addr, app_port=5000)
        
        print("App URL:%s" % app_url)
        return app_url

    def deploy(self, deploy_type, deploy_name):
        print("Local deployer called for app %s" % self.task_def.app_data['app_name'])

        if deploy_type == 'service':
            service_ip_addr = self._deploy_service_container(deploy_name)
            ip_addr = service_ip_addr
        elif deploy_type == 'app':
            app_ip_addr = self._deploy_app_container()
            ip_addr = app_ip_addr
             
        return ip_addr