'''
Created on Nov 2, 2016

@author: devdatta
'''
import logging
import json 
import tarfile
import urllib2
import os
import codecs
import gzip
import sys

class Deployment(object):

    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)

    def __init__(self):
        pass

    def _make_tarfile(self, output_filename, source_dir):
        with tarfile.open(output_filename, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))

    def _read_tarfile(self, tarfile_name):
        with gzip.open(tarfile_name, "rb") as f:
            contents = f.read()
            return contents

    def post(self, app_path, app_info, service_info, cloud='local'):
        source_dir = app_path
        k = source_dir.rfind("/")
        app_name = source_dir[k+1:]
        tarfile_name = app_name + ".tar"

        self._make_tarfile(tarfile_name, source_dir)
        tarfile_content = self._read_tarfile(tarfile_name)

        cloud = cloud

        app_type = app_info['app_type']
        entry_point = app_info['entrypoint']
        app_data = {'app_name':app_name, 'app_tar_name': tarfile_name, 
                    'app_content':tarfile_content, 'app_type': app_type,
                    'run_cmd': entry_point}

        cloud_data = {'cloud': cloud}

        service_list = []
        if bool(service_info):
            service_name = service_info['service_name']
            service_type = service_info['service_type']
            service_details = {'db_var': 'DB', 'host_var': 'HOST',
                               'user_var': 'USER', 'password_var': 'PASSWORD',
                               'db_name': 'checkout'}

            service_data = {'service_name':service_name, 'service_type': service_type,
                            'service_details': service_details}
            service_list.append(service_data)

        data = {'app': app_data, 'service': service_list, 'cloud': cloud_data}

        req = urllib2.Request("http://localhost:5002/deployments")
        #req = urllib2.Request("http://127.0.0.1:5000/deployments")
        #req = urllib2.Request("http://192.168.33.10:5000/deployments")
        req.add_header('Content-Type', 'application/octet-stream')

        response = urllib2.urlopen(req, json.dumps(data, ensure_ascii=True, encoding='ISO-8859-1'))
        track_url = response.headers.get('location')
        self.log.debug("Deployment ID:%s" % track_url)
        return track_url

    def get(self, dep_id):
        app_url = "http://localhost:5002/deployments/" + dep_id
        req = urllib2.Request(app_url)
        response = urllib2.urlopen(req)
        app_data = response.fp.read()
        self.log.debug("Response:%s" % app_data)
        return app_data

    def get_app_info(self, appname):
        app_url = "http://localhost:5002/apps/" + appname
        req = urllib2.Request(app_url)
        response = urllib2.urlopen(req)
        app_data = response.fp.read()
        self.log.debug("Response:%s" % app_data)
        return app_data

    def get_cloud_info(self, cloud):
        app_url = "http://localhost:5002/clouds/" + cloud
        req = urllib2.Request(app_url)
        response = urllib2.urlopen(req)
        app_data = response.fp.read()
        self.log.debug("Response:%s" % app_data)
        return app_data
