'''
Created on Oct 27, 2016

@author: devdatta
'''
class App(object):
    
    def __init__(self, app_data):
        self.app_data = app_data
        self.app_name = app_data['app_name']
        self.app_location = app_data['app_location']
        
    def get_cont_name(self):                
        k = self.app_location.rfind("/")
        app_loc = self.app_location[k+1:]
        app_loc = app_loc.replace(":","-")
        cont_name = self.app_name + "-" + app_loc                
        return cont_name

    def update_app_status(self, status):
        app_status_file = open(self.app_location + "/app-status.txt", "a")
        app_status_file.write(status + ", ")
        app_status_file.close()

    def update_app_ip(self, app_ip):
        app_status_file = open(self.app_location + "/app-status.txt", "a")
        app_status_file.write("App URL: http://" + app_ip)
        app_status_file.close()
        
    