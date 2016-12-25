'''
Created on Dec 24, 2016

@author: devdatta
'''
class Service(object):
    "Helper class that knows how to obtain service information"

    def __init__(self, service_data):
        self.service_data = service_data

    def get_service_type(self):
        return self.service_data['service']['type']    

    def get_service_name(self):
        return self.get_service_type()
    
    def get_setup_file_content(self):
        return self.service_data['service']['setup_script_content']

    def get_service_prov_work_location(self):
        return self.service_data['service_location']

    def get_status_file_location(self):
        return self.get_service_prov_work_location() + "/service-status.txt"

    def get_service_details_file_location(self):
        return self.get_service_prov_work_location() + "/service-details.txt"

    def get_service_version(self):
        return self.service_data['service_version']
    
