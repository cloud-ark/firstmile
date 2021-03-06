import logging
import json 
import tarfile
import urllib2
import os
import gzip
import requests
import sys

import common


class Deployment(object):

    DOCKER_HOST='localhost'

    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)

    def __init__(self):
        docker_host_file_path = os.path.dirname(sys.modules[__name__].__file__)
        if os.path.exists(docker_host_file_path + "/docker_host.txt"):
            fp = open(docker_host_file_path + "/docker_host.txt", "r")
            line = fp.readline()
            parts = line.split("=")
            Deployment.DOCKER_HOST=parts[1].strip()

    def _make_tarfile(self, output_filename, source_dir):
        with tarfile.open(output_filename, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))

    def _delete_tarfile(self, tarfile_name, source_dir):
        cwd = os.getcwd()
        os.chdir(source_dir)
        if os.path.exists(tarfile_name):
            os.remove(tarfile_name)
        os.chdir(cwd)

    def _read_tarfile(self, tarfile_name):
        with gzip.open(tarfile_name, "rb") as f:
            contents = f.read()
            return contents

    def _parse_service_info(self, service_info):
        service_list = []

        for service_type, service_obj in service_info.items():
            service_name = service_type
            service_type = service_type #service_info['service_type']
            db_var = service_obj['service']['app_variables']['db_var']
            host_var = service_obj['service']['app_variables']['host_var']
            user_var = service_obj['service']['app_variables']['user_var']
            password_var = service_obj['service']['app_variables']['password_var']
            setup_script = service_obj['service']['setup_script']
            #db_name = service_info['db_name']

            service_details = {'db_var': db_var, 'host_var': host_var,
                               'user_var': user_var, 'password_var': password_var,
                               'setup_script': setup_script}

            service_data = {'service_name':service_name, 'service_type': service_type,
                            'service_details': service_details}
            service_list.append(service_data)
        return service_list

    def create_service_instance(self, service_info, cloud_info):
        #service_list = self._parse_service_info(service_info)
        req_url = ("http://{host}:5002/deployments").format(host=Deployment.DOCKER_HOST)
        req = urllib2.Request(req_url)
        #req = urllib2.Request("http://127.0.0.1:5000/deployments")
        #req = urllib2.Request("http://192.168.33.10:5000/deployments")
        req.add_header('Content-Type', 'application/octet-stream')

        data = {'service': service_info, 'cloud': cloud_info}

        response = urllib2.urlopen(req, json.dumps(data, ensure_ascii=True, encoding='ISO-8859-1'))

        if response.code == '503':
            common.diskfull_error_response()
            return

        track_url = response.headers.get('location')
        self.log.debug("Deployment ID:%s" % track_url)
        return track_url

    def post(self, app_path, app_info, service_info, cloud_info):
        source_dir = app_path
        k = source_dir.rfind("/")
        app_name = source_dir[k+1:]
        tarfile_name = app_name + ".tar"

        self._make_tarfile(tarfile_name, source_dir)
        tarfile_content = self._read_tarfile(tarfile_name)

        app_type = app_info['app_type']
        entry_point = app_info['entry_point']

        app_info['app_name'] = app_name
        app_info['app_tar_name'] = tarfile_name
        app_info['app_content'] = tarfile_content
        app_info['app_type'] = app_type
        app_info['entry_point'] = entry_point

        data = {'app': app_info, 'service': service_info, 'cloud': cloud_info}

        req_url=("http://{host}:5002/deployments").format(host=Deployment.DOCKER_HOST)
        req = urllib2.Request(req_url)
        #req = urllib2.Request("http://127.0.0.1:5000/deployments")
        #req = urllib2.Request("http://192.168.33.10:5000/deployments")
        req.add_header('Content-Type', 'application/octet-stream')

        response = urllib2.urlopen(req, json.dumps(data, ensure_ascii=True, encoding='ISO-8859-1'))

        if response.code == '503':
            common.diskfull_error_response()
            return
        track_url = response.headers.get('location')
        self.log.debug("Deployment ID:%s" % track_url)

        self._delete_tarfile(tarfile_name, source_dir)

        return track_url

    def service_delete(self, dep_id):
        app_url = ("http://{host}:5002/servicesdep/").format(host=Deployment.DOCKER_HOST)
        app_url = app_url + dep_id
        response = requests.delete(app_url)
        if response.status_code == 404:
            print("Service with deploy-id %s not found." % dep_id)
        if response.status_code == 202:
            print("Request to delete service with deploy-id %s accepted." % dep_id)
        return response

    def service_secure(self, dep_id):
        app_url = ("http://{host}:5002/servicesdep/").format(host=Deployment.DOCKER_HOST)
        app_url = app_url + dep_id
        response = requests.put(app_url)
        if response.status_code == 404:
            print("Service with deploy-id %s not found." % dep_id)
        if response.status_code == 405:
            print("Request to secure service with deploy-id %s not supported as it is a local service." % dep_id)
        if response.status_code == 202:
            print("Request to secure service with deploy-id %s accepted." % dep_id)
        return response


    def delete(self, dep_id):
        app_url = ("http://{host}:5002/deployments/").format(host=Deployment.DOCKER_HOST)
        app_url = app_url + dep_id
        response = requests.delete(app_url)
        if response.status_code == 404:
            print("Application with deploy-id %s not found." % dep_id)
        if response.status_code == 202:
            print("Request to delete application with deploy-id %s accepted." % dep_id)
        return response

    def logs(self, dep_id):
        app_url = ("http://{host}:5002/logs/").format(host=Deployment.DOCKER_HOST)
        app_url = app_url + dep_id
        req = urllib2.Request(app_url)
        app_data = ''
        try:
            response = urllib2.urlopen(req)
            app_data = response.fp.read()
            self.log.debug("Response:%s" % app_data)
        except urllib2.HTTPError as e:
            if e.getcode() == 404:
                print("Application with deploy-id %s not found." % dep_id)
        return app_data

    def get(self, dep_id):
        app_url = ("http://{host}:5002/deployments/").format(host=Deployment.DOCKER_HOST)
        app_url = app_url + dep_id
        req = urllib2.Request(app_url)
        app_data = ''
        try:
            response = urllib2.urlopen(req)
            app_data = response.fp.read()
            self.log.debug("Response:%s" % app_data)
        except urllib2.HTTPError as e:
            if e.getcode() == 404:
                print("Application with deploy-id %s not found." % dep_id)
        return app_data

    def get_all_apps(self):
        app_url = ("http://{host}:5002/apps").format(host=Deployment.DOCKER_HOST)
        req = urllib2.Request(app_url)
        response = urllib2.urlopen(req)
        app_data = response.fp.read()
        self.log.debug("Response:%s" % app_data)
        return app_data

    def get_app_info(self, appname):
        app_url = ("http://{host}:5002/apps/").format(host=Deployment.DOCKER_HOST)
        app_url = app_url + appname
        req = urllib2.Request(app_url)
        app_data = ''
        try:
            response = urllib2.urlopen(req)
            app_data = response.fp.read()
            self.log.debug("Response:%s" % app_data)
        except urllib2.HTTPError as e:
            if e.getcode() == 404:
                print("Application with name %s not found." % appname)
        return app_data

    def get_all_services(self):
        app_url = ("http://{host}:5002/services").format(host=Deployment.DOCKER_HOST)
        req = urllib2.Request(app_url)
        response = urllib2.urlopen(req)
        service_data = response.fp.read()
        self.log.debug("Response:%s" % service_data)
        return service_data

    def get_service_info(self, service_name):
        service_url = ("http://{host}:5002/services/").format(host=Deployment.DOCKER_HOST)
        service_url = service_url + service_name
        req = urllib2.Request(service_url)
        response = urllib2.urlopen(req)
        service_data = response.fp.read()
        self.log.debug("Response:%s" % service_data)
        return service_data

    def get_service_info_from_id(self, deploy_id):
        service_url = ("http://{host}:5002/servicesdep/").format(host=Deployment.DOCKER_HOST)
        service_url = service_url + deploy_id
        req = urllib2.Request(service_url)
        response = urllib2.urlopen(req)
        service_data = response.fp.read()
        self.log.debug("Response:%s" % service_data)
        return service_data

    def get_cloud_info(self, cloud):
        improper_input = common.verify_cloud(cloud)
        if improper_input:
            exit()
        app_url = ("http://{host}:5002/clouds/").format(host=Deployment.DOCKER_HOST)
        app_url = app_url + cloud
        req = urllib2.Request(app_url)
        response = urllib2.urlopen(req)
        app_data = response.fp.read()
        self.log.debug("Response:%s" % app_data)
        return app_data
