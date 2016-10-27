'''
Created on Oct 26, 2016

@author: devdatta
'''

class LocalBuilder(object):
    
    def __init__(self, task_def):
        self.task_def = task_def
        
    def _build_service_container(self):
        pass
    
    def _build_app_container(self):
        pass
        
    def build(self, build_type, build_name):
        print("Local builder called for app %s" % self.task_def.app_data['app_name'])
        
        if build_type == 'service':
            self._build_service_container()
        elif build_type == 'app':
            self._build_app_container()
        
        return 0
