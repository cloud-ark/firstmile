import json
import tarfile
import urllib2
import os
import codecs
import gzip

def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

def read_tarfile(tarfile_name):
    with gzip.open(tarfile_name, "rb") as f:
        contents = f.read()
        return contents

app_name = 'app1'
tarfile_name = 'app11.tar'
source_dir = './tmp/test'

make_tarfile(tarfile_name, source_dir)
tarfile_content = read_tarfile(tarfile_name)

data = {'app_name':app_name, 'app_tar_name': tarfile_name, 'app_content':tarfile_content}

req = urllib2.Request("http://localhost:5000/deployments")
req.add_header('Content-Type', 'application/octet-stream')

response = urllib2.urlopen(req, json.dumps(data))
