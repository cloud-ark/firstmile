'''
Created on Oct 26, 2016

@author: devdatta
'''
import threading
from common import task_definition as td
from builder import builder as bld
from generator import generator as gen
from deployer import deployer as dep

class Manager(threading.Thread):
    
    def __init__(self, name, task_def):
        threading.Thread.__init__(self)
        self.task = task_def
        self.app_name = task_def.task_definition['app_name']
        self.app_location = task_def.task_definition['app_location']
        self.name = name
        
    def run(self):
        print "Starting " + self.name
        print("Task received: %s" % self.task.task_definition)
        bld.Builder(self.task).build()
        gen.Generator(self.task).generate()
        dep.Deployer(self.task).deploy()
        
        

        
    
        

