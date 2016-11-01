import json
import tarfile
import urllib2
import os
import codecs
import gzip
import sys

class Deployment(object):

    def __init__(self):
        pass

    def _make_tarfile(self, output_filename, source_dir):
        with tarfile.open(output_filename, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))

    def _read_tarfile(self, tarfile_name):
        with gzip.open(tarfile_name, "rb") as f:
            contents = f.read()
            return contents

    def post(self):
        #app_name = raw_input("Enter app name:")
        app_name = 'express-checkout'
        tarfile_name = app_name + ".tar"
        #source_dir = raw_input("Enter app directory:")
        source_dir = './express-checkout'

        self._make_tarfile(tarfile_name, source_dir)
        tarfile_content = self._read_tarfile(tarfile_name)

        cloud = 'local'
        service_name = 'mysql-service'
        service_type = 'mysql'

        app_data = {'app_name':app_name, 'app_tar_name': tarfile_name, 
                    'app_content':tarfile_content, 'app_type': 'python',
                    'run_cmd': 'application.py'}
        cloud_data = {'cloud': cloud}

        service_details = {'db_var': 'DB', 'host_var': 'HOST', 
                           'user_var': 'USER', 'password_var': 'PASSWORD',
                           'db_name': 'checkout'}

        service_data = {'service_name':service_name, 'service_type': service_type, 
                        'service_details': service_details}

        data = {'app': app_data, 'service': [service_data], 'cloud': cloud_data}

        req = urllib2.Request("http://localhost:5000/deployments")
        req.add_header('Content-Type', 'application/octet-stream')

        response = urllib2.urlopen(req, json.dumps(data, ensure_ascii=True, encoding='ISO-8859-1'))
        print("Deployment ID:%s" % response.headers.get('location'))

    def get(self, app_url):
        req = urllib2.Request(app_url)
        response = urllib2.urlopen(req)
        app_data = response.fp.read()
        print("Response:%s" % app_data)


if __name__ == '__main__':

    dep = Deployment()

    if sys.argv[1].lower() == 'post':
        dep.post()
    if sys.argv[1].lower() == 'get':
        app_url = sys.argv[2]
        dep.get(app_url)

    print("Done.")

