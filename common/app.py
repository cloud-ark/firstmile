'''
Created on Oct 27, 2016

@author: devdatta
'''
class App(object):

    def __init__(self, app_data):
        self.app_data = app_data
        self.app_name = app_data['app_name']
        self.app_location = app_data['app_location']
        
        self.service_app_varlist = {}
        self.mysql_app_vars = ["db_var", "host_var", "user_var", "password_var"]

        self.service_app_varlist['mysql'] = self.mysql_app_vars

    def get_app_varlist(self, service_name):
        return self.service_app_varlist[service_name]

    def get_cont_name(self):                
        k = self.app_location.rfind("/")
        app_loc = self.app_location[k+1:]
        app_loc = app_loc.replace(":","-")
        cont_name = self.app_name + "-" + app_loc                
        return cont_name

    def get_entrypoint_file_name(self):
        entry_point = self.app_data['entry_point']
        k = entry_point.index(".py")
        entry_point = entry_point[:k]
        return entry_point

    def update_app_status(self, status):
        app_status_file = open(self.app_location + "/app-status.txt", "a")
        status = "status::" + status
        app_status_file.write(status + ", ")
        app_status_file.flush()
        app_status_file.close()

    def update_app_ip(self, app_ip):
        app_status_file = open(self.app_location + "/app-status.txt", "a")
        if app_ip.find("http") < 0:
            app_ip = "http://" + app_ip
        app_status_file.write("URL:: " + app_ip)
        app_status_file.flush()
        app_status_file.close()
        
    