'''
Created on Dec 19, 2016

@author: devdatta
'''
import os
import subprocess
import logging

class DockerLib(object):

    def __init__(self):
        self.docker_file_snippets = {}
        self.docker_file_snippets['aws'] = self._aws_df_snippet()

    def _aws_df_snippet(self):
        #df = ("FROM ubuntu:14.04\n"
        #      "RUN apt-get update && apt-get install -y \ \n"
        #      "      python-setuptools python-pip git groff \n"
        #      "RUN pip install awsebcli==3.7.7 \n"
        #      "RUN pip install awscli==1.10.63 \n")
        df = ("FROM lmecld/clis:awscli\n")
        return df

    def get_dockerfile_snippet(self, key):
        return self.docker_file_snippets[key]

    def _get_cont_id(self, cont_name):
        cont_id_cmd = ("docker ps -a | grep {cont_name} | cut -d ' ' -f 1").format(cont_name=cont_name)

        out = subprocess.Popen(cont_id_cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=True).communicate()[0]
        return out

    def stop_container(self, cont_name, reason_phrase):
        logging.debug("Stopping container %s. Reason: %s" % (cont_name, reason_phrase))
        cont_id = self._get_cont_id(cont_name)
        if cont_id:
            stop_cmd = ("docker stop {cont_id}").format(cont_id=cont_id)
            logging.debug("stop command:%s" % stop_cmd)
            os.system(stop_cmd)

    def remove_container(self, cont_name, reason_phrase):
        logging.debug("Removing container %s. Reason: %s" % (cont_name, reason_phrase))
        cont_id = self._get_cont_id(cont_name)
        if cont_id:
            rm_cmd = ("docker rm -f {cont_id}").format(cont_id=cont_id)
            #rm_cmd = ("docker ps -a | grep {cont_name} | cut -d ' ' -f 1 | xargs docker rm -f").format(cont_name=cont_name)
            logging.debug("rm command:%s" % rm_cmd)
            os.system(rm_cmd)

    def remove_container_image(self, cont_name, reason_phrase):
        logging.debug("Removing container image %s. Reason: %s" % (cont_name, reason_phrase))
        #cont_id = self._get_cont_id(cont_name)
        #if cont_id:
        #rmi_cmd = ("docker rmi -f {cont_id}").format(cont_id=cont_id)
        cont_id_cmd = ("docker images -a | grep {cont_name}  | awk \'{{print $3}}\'").format(cont_name=cont_name)

        cont_id = subprocess.Popen(cont_id_cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=True).communicate()[0]
        if cont_id:
            rmi_cmd =  ("docker rmi -f {cont_id}").format(cont_id=cont_id)
            logging.debug("rmi command:%s" % rmi_cmd)
            os.system(rmi_cmd)

    def build_container_image(self, cont_name, docker_file_name):
        docker_build_cmd = ("docker build -t {cont_name} -f {docker_file_name} .").format(cont_name=cont_name,
                                                                                          docker_file_name=docker_file_name)
        logging.debug("Docker build cmd:%s" % docker_build_cmd)
        os.system(docker_build_cmd)

    def run_container(self, cont_name):
        docker_run_cmd = ("docker run -i -t -d {cont_name}").format(cont_name=cont_name)
        logging.debug("Docker run cmd:%s" % docker_run_cmd)
        os.system(docker_run_cmd)

    
    