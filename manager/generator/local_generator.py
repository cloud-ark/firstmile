'''
Created on Oct 26, 2016

@author: devdatta
'''
class LocalGenerator(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        self.app_type = task_def.app_data['app_type']
        self.app_dir = task_def.app_data['app_location']
        
    def _generate_for_python_app(self, service_ip_dict):
        
        serv = self.task_def.service_data[0]
        service_name = serv['service_name']
        
        DB = serv['service_details']['db_var']
        db_name = serv['service_details']['db_name']
        USER = serv['service_details']['user_var']        
        PASSWORD = serv['service_details']['password_var']
        HOST = serv['service_details']['host_var']
        
        for k, v in service_ip_dict.items():
            if k == service_name:
                host = v
        
        run_cmd = self.task_def.app_data['run_cmd']
               
        df = ("FROM ubuntu:14.04\n"
              "RUN apt-get update -y\n"
              "RUN apt-get install -y python-setuptools\n"
              "ADD .\n"
              "pip install -r requirements.txt\n"
              "EXPOSE 5000\n"
              "ENV {DB} {db_name}\n"
              "ENV {USER} lmeuser\n"
              "ENV {PASSWORD} lmeuserpass\n"
              "ENV {HOST} {host}\n"
              "CMD \"{run_cmd}\"\n"
              "").format(DB=DB, db_name=db_name, USER=USER, 
                         PASSWORD=PASSWORD, HOST=HOST, host=host, run_cmd=run_cmd)
        
        print("App dir: %s" % self.app_dir)
        docker_file = open(self.app_dir + "/Dockerfile", "w")
        docker_file.write(df)
        docker_file.close()

        
    def generate(self, service_ip_dict):
        print("Local generator called for app %s" % self.task_def.app_data['app_name'])
        
        if self.app_type == 'python':
            self._generate_for_python_app(service_ip_dict)
        else:
            print("Application of type %s not supported." % self.app_type)        
        return 0