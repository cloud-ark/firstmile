import os
import tarfile
import datetime
import time

from os.path import expanduser

from flask import Flask, jsonify, request
from flask_restful import reqparse, abort, Resource, Api


from manager import manager as mgr
from common import task_definition

app = Flask(__name__)
api = Api(app)

parser = reqparse.RequestParser()
parser.add_argument('app_content', location='form')
parser.add_argument('app_name', location='form')

home_dir = expanduser("~")

APP_STORE_PATH = ("{home_dir}/.lme/data/deployments").format(home_dir=home_dir)


class Deployment(Resource):
    def get(self, dep_id):
        return {'LME': 'This is LME'}

class Deployments(Resource):
    def _untar_the_app(self, app_tar_file, versioned_app_path):
        #TODO(devkulkarni): Untaring is not working
        #os.chdir(versioned_app_path)
        #tar = tarfile.open(app_tar_name)
        #for member in tar.getmembers():
        #    tar.extractfile(member)
        #tar.close()

        untar_cmd = ("tar -xvf {app_tar_file} -C {versioned_app_path}").format(app_tar_file=app_tar_file,
                                                                               versioned_app_path=versioned_app_path)
        os.system(untar_cmd)

    def _store_app_contents(self, app_name, app_tar_name, content):
        # create directory
        app_path = ("{APP_STORE_PATH}/{app_name}").format(APP_STORE_PATH=APP_STORE_PATH, app_name=app_name)
        if not os.path.exists(app_path):
            os.makedirs(app_path)

        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H:%M:%S')

        versioned_app_path = ("{app_path}/{st}").format(app_path=app_path, st=st)
        os.makedirs(versioned_app_path)

        # store file content
        app_tar_file = ("{versioned_app_path}/{app_tar_name}").format(versioned_app_path=versioned_app_path, 
                                                                      app_tar_name=app_tar_name)
        app_file = open(app_tar_file, "w")
        app_file.write(content)

        # expand the directory
        self._untar_the_app(app_tar_file, versioned_app_path)
        return versioned_app_path
    
    def post(self):
        #args = parser.parse_args()
        args = request.get_json(force=True)
        print(args)
        
        app_data = args['app']
        cloud_data = args['cloud']
        service_data = args['service']
        
        app_name = app_data['app_name']
        app_tar_name = app_data['app_tar_name']
        content = app_data['app_content']
        cloud = cloud_data['cloud']

        app_location = self._store_app_contents(app_name, app_tar_name, content)
        
        # dispatch the handler thread
        #task_dict = {}
        #task_dict['app_name'] = app_name
        #task_dict['app_location'] = app_location
        #task_dict['cloud'] = cloud
        app_data['app_location'] = app_location
        task_def = task_definition.TaskDefinition(app_data, cloud_data, service_data)
        delegatethread = mgr.Manager(app_name, task_def)
        delegatethread.start()        

        return content, 201

api.add_resource(Deployment, '/deployments/<dep_id>')
api.add_resource(Deployments, '/deployments')

if __name__ == '__main__':
    # Create the data directory if it does not exist
    if not os.path.exists(APP_STORE_PATH):
        os.makedirs(APP_STORE_PATH)
    app.run(debug=True)
