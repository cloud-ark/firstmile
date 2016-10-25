import os
import tarfile
import datetime
import time

from flask import Flask, jsonify, request
from flask_restful import reqparse, abort, Resource, Api

app = Flask(__name__)
api = Api(app)

parser = reqparse.RequestParser()
parser.add_argument('app_content', location='form')
parser.add_argument('app_name', location='form')

APP_STORE_PATH = "../data/deployments"

class HelloWorld(Resource):
    def get(self):
        return {'hello': 'world'}

class Deployment(Resource):
    def get(self, dep_id):
        return {'LME': 'This is LME'}

class Deployments(Resource):
    def _untar_the_app(self, versioned_app_path, app_tar_name):
        #os.chdir(versioned_app_path)
        #tar = tarfile.open(app_tar_name)
        #for member in tar.getmembers():
        #    tar.extractfile(member)
        #tar.close()

        untar_cmd = ("tar -xvf {versioned_app_path}/{app_tar_name} -C {versioned_app_path}").format(versioned_app_path=versioned_app_path, app_tar_name=app_tar_name)
        os.system(untar_cmd)

    def _store_app_contents(self, app_name, app_tar_name, content):
        # create directory
        app_path = APP_STORE_PATH + "/" + app_name
        if not os.path.exists(app_path):
            os.makedirs(app_path)

        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H:%M:%S')

        versioned_app_path = app_path + "/" + st
        os.makedirs(versioned_app_path)

        # store file content
        app_file = open(versioned_app_path + "/" + app_tar_name, "w")
        app_file.write(content)

        # expand the directory
        self._untar_the_app(versioned_app_path, app_tar_name)
    
    def post(self):
        #args = parser.parse_args()
        args = request.get_json(force=True)
        app_name = args['app_name']
        app_tar_name = args['app_tar_name']
        content = args['app_content']

        self._store_app_contents(app_name, app_tar_name, content)

        return content, 201

api.add_resource(HelloWorld, '/')
api.add_resource(Deployment, '/deployments/<dep_id>')
api.add_resource(Deployments, '/deployments')

if __name__ == '__main__':
    # Create the data directory if it does not exist
    if not os.path.exists(APP_STORE_PATH):
        os.makedirs(APP_STORE_PATH)
    app.run(debug=True)
