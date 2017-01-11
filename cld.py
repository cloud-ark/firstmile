import logging
import os
import subprocess
import tarfile
import datetime
import time
import thread

from os.path import expanduser

from flask import Flask, jsonify, request
from flask_restful import reqparse, abort, Resource, Api

from manager import manager as mgr
from common import task_definition
from common import utils
from common import service


app = Flask(__name__)
api = Api(app)

parser = reqparse.RequestParser()
parser.add_argument('app_content', location='form')
parser.add_argument('app_name', location='form')

home_dir = expanduser("~")

APP_STORE_PATH = ("{home_dir}/.cld/data/deployments").format(home_dir=home_dir)
SERVICE_STORE_PATH = APP_STORE_PATH + "/services"

def start_thread(delegatethread):
    try:
        delegatethread.run()
    except Exception as e:
        logging.error(e)

class Cloud(Resource):

    def _get(self, cloud_name):
        app_lines = list()
        f = open(APP_STORE_PATH + "/app_ids.txt")
        all_lines = f.readlines()
        for line in all_lines:
            line_contents = line.split(" ")
            app_line = {}

            app_version = line_contents[1]
            k = app_version.find("--")
            app_name = app_version[:k]
            app_version = app_version[k+2:].rstrip().lstrip()
            found_cloud = line_contents[2].rstrip().lstrip()

            if found_cloud == cloud_name:
                app_stat_file = APP_STORE_PATH + "/" + app_name + "/" + app_version + "/app-status.txt"

                if os.path.exists(app_stat_file):
                    app_line['dep_id'] = line_contents[0]
                    app_line['app_version'] = app_version
                    app_line['app_name'] = app_name
                    app_stat_file = open(app_stat_file)
                    stat_line = app_stat_file.read()

                    parts = stat_line.split(',')
                    cloud = ''
                    url = ''
                    for p in parts:
                        if p.find("cloud::") >= 0:
                            cld = p.split("::")
                            if len(cld) > 2:
                                cloud = cld[2]
                            else:
                                cloud = cld[1]
                        if p.find("URL::") >= 0:
                            u = p.split("::")
                            url = u[1]
                    app_line['cloud'] = cloud
                    app_line['url'] = url

                    app_lines.append(app_line)

        return app_lines

    def get(self, cloud_name):
        logging.debug("Executing GET for cloud:%s" % cloud_name)
        app_lines = list()

        if os.path.exists(APP_STORE_PATH + "/app_ids.txt"):
            app_lines = self._get(cloud_name)

        resp_data = {}

        resp_data['app_data'] = app_lines

        response = jsonify(**resp_data)
        response.status_code = 201
        return response

class Service(Resource):
    def get(self, service_name):
        logging.debug("Executing GET for service:%s" % service_name)

        status_lines = utils.read_statues(SERVICE_STORE_PATH, "service_ids.txt", 
                                          "service-status.txt", service_name, '')
        status_and_details_lines = utils.read_service_details(SERVICE_STORE_PATH, "service_ids.txt",
                                                              "service-details.txt", service_name, '', status_lines)

        resp_data = {}

        resp_data['data'] = status_and_details_lines

        response = jsonify(**resp_data)
        response.status_code = 201
        return response

class ServiceGetDeployID(Resource):
    def get(self, dep_id):
        logging.debug("Executing GET for deploy id:%s" % dep_id)

        resp_data = {}
        stat_and_details_lines = list()

        service_name, service_version = utils.get_artifact_name_version(SERVICE_STORE_PATH,
                                                                "service_ids.txt",
                                                                "service-status.txt",
                                                                dep_id)

        if service_name and service_version:
            status_data = utils.read_statuses_given_id(SERVICE_STORE_PATH,
                                                       "service_ids.txt",
                                                       "service-status.txt",
                                                       dep_id)

            stat_and_details_lines = utils.read_service_details(SERVICE_STORE_PATH,
                                                                "service_ids.txt",
                                                                "service-details.txt",
                                                                service_name, service_version,
                                                                status_data)

        resp_data['data'] = stat_and_details_lines
        response = jsonify(**resp_data)
        response.status_code = 201
        return response

class App(Resource):
    def get(self, app_name):
        logging.debug("Executing GET for app:%s" % app_name)

        status_lines = utils.read_statues(APP_STORE_PATH, "app_ids.txt",
                                          "app-status.txt", app_name, '')
        resp_data = {}

        resp_data['data'] = status_lines

        response = jsonify(**resp_data)
        response.status_code = 201
        return response

class Deployment(Resource):
    def get(self, dep_id):
        logging.debug("Executing GET for dep id:%s" % dep_id)
        status_data = utils.read_statuses_given_id(APP_STORE_PATH,
                                                   "app_ids.txt",
                                                   "app-status.txt",
                                                   dep_id)
        resp_data = {}

        resp_data['data'] = status_data

        response = jsonify(**resp_data)
        response.status_code = 201
        return response

    def get_1(self, dep_id):
        logging.debug("Executing GET for dep id:%s" % dep_id)

        def _get_app_location(app_id):

            f = open(APP_STORE_PATH + "/app_ids.txt")
            all_lines = f.readlines()
            for line in all_lines:
                line_contents = line.split(" ")
                if line_contents[0] == app_id:
                    dep_id = line_contents[1].rstrip().lstrip()
                    break

            k = dep_id.rfind("--")
            app_version = dep_id[k+2:]
            logging.debug("App version:%s" % app_version)

            dep_id = dep_id[:k]
            l = dep_id.rfind("/")
            app_name = dep_id[l+1:]
            logging.debug("App name:%s" % app_name)
            return APP_STORE_PATH + "/" + app_name + "/" + app_version

        app_location = _get_app_location(dep_id)
        logging.debug("App location:%s" % app_location)

        try:
            app_status_data = "No status available yet."
            status_file = app_location + "/app-status.txt"
            app_status_file = open(status_file, "r")
            app_status_data = app_status_file.read()
            logging.debug("--- App status ---")
            logging.debug(app_status_data)
            logging.debug("--- App status ---")
        except IOError:
            logging.error("Status file does not exist:%s" % str(status_file))
            logging.error("App status: %s" % app_status_data)
        
        resp_data = {}
        resp_data['app_data'] = app_status_data

        response = jsonify(**resp_data)
        response.status_code = 201
        return response

class Deployments(Resource):
    def _untar_the_app(self, app_tar_file, versioned_app_path):
        #TODO(devkulkarni): Untaring is not working
        #os.chdir(versioned_app_path)
        #tar = tarfile.open(app_tar_name)
        #for member in tar.getmembers():
        #    tar.extractfile(member)
        #tar.close()

        logging.debug("Untarring received app tar file %s" % app_tar_file)

        untar_cmd = ("tar -xf {app_tar_file} -C {versioned_app_path}").format(app_tar_file=app_tar_file,
                                                                               versioned_app_path=versioned_app_path)

        result = subprocess.check_output(untar_cmd, shell=True)
        logging.debug(result)

    def _store_service_contents(self, service_name, setup_file_content, version):
        service_path = ("{SERVICE_STORE_PATH}/{service_name}").format(SERVICE_STORE_PATH=SERVICE_STORE_PATH,
                                                                      service_name=service_name)
        if not os.path.exists(service_path):
            os.makedirs(service_path)

        ts = time.time()

        if version:
            service_version = version
        else:
            service_version = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S')

        versioned_service_path = ("{service_path}/{st}").format(service_path=service_path, st=service_version)
        os.makedirs(versioned_service_path)

        if setup_file_content:
            setup_file = open(versioned_service_path + "/setup.sh", "w")
            setup_file.write(setup_file_content.encode("ISO-8859-1"))
            setup_file.close()
        return versioned_service_path, service_version

    def _store_app_contents(self, app_name, app_tar_name, content):
        # create directory
        app_path = ("{APP_STORE_PATH}/{app_name}").format(APP_STORE_PATH=APP_STORE_PATH, app_name=app_name)
        if not os.path.exists(app_path):
            os.makedirs(app_path)

        ts = time.time()
        app_version = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S')

        versioned_app_path = ("{app_path}/{st}").format(app_path=app_path, st=app_version)
        os.makedirs(versioned_app_path)

        # store file content
        app_tar_file = ("{versioned_app_path}/{app_tar_name}").format(versioned_app_path=versioned_app_path, 
                                                                      app_tar_name=app_tar_name)
        app_file = open(app_tar_file, "w")
        app_file.write(content.encode("ISO-8859-1"))

        # expand the directory
        self._untar_the_app(app_tar_file, versioned_app_path)
        return versioned_app_path, app_version

    def _update_service_data(self, service_data, service_name, version):
        service_obj = service.Service(service_data[0])
        setup_file_content = service_obj.get_setup_file_content()
        service_location, service_version = self._store_service_contents(service_name,
                                                                         setup_file_content,
                                                                         version)
        service_data[0]['service_location'] = service_location
        service_data[0]['service_version'] = service_version
        return service_data, service_version

    # Handle service, app, and app+service deployments
    def post(self):
        #args = parser.parse_args()
        logging.debug("Received POST request.")
        args = request.get_json(force=True)
        
        response = jsonify()
        response.status_code = 201

        args_dict = dict(args)

        # Handle service deployment
        if not 'app' in args_dict and (args_dict['service'] and args_dict['cloud']):
            cloud_data = args['cloud']
            cloud = cloud_data['type']
            service_data = args['service']

            # Currently supporting single service
            service_obj = service.Service(service_data[0])
            task_name = service_name = service_obj.get_service_name()

            version = '' # get new version for service deployment
            service_data, service_version = self._update_service_data(service_data,
                                                                      service_name,
                                                                      version)

            task_def = task_definition.TaskDefinition('', cloud_data, service_data)

            service_id = utils.get_id(SERVICE_STORE_PATH, "service_ids.txt", service_name, 
                                  service_version, '', '', cloud)
            logging.debug("Service id:%s" % service_id)
            response.headers['location'] = ('/deployments/{service_id}').format(service_id=service_id)
        elif args['app'] and args['service'] and args['cloud']: #handle app and service deployment
            app_data = args['app']
            cloud_data = args['cloud']
            service_data = args['service']

            task_name = app_name = app_data['app_name']
            app_tar_name = app_data['app_tar_name']
            content = app_data['app_content']
            cloud = cloud_data['type']

            app_location, app_version = self._store_app_contents(app_name, app_tar_name, content)
            app_data['app_location'] = app_location
            app_data['app_version'] = app_version

            service_name = service.Service(service_data[0]).get_service_name() + "-" + app_name
            service_data, service_version = self._update_service_data(service_data,
                                                                      service_name,
                                                                      app_version)

            task_def = task_definition.TaskDefinition(app_data, cloud_data, service_data)

            app_id = utils.get_id(APP_STORE_PATH, "app_ids.txt", app_name, app_version,
                                  service_name, service_version, cloud)
            logging.debug("App id:%s" % app_id)
            response.headers['location'] = ('/deployments/{app_id}').format(app_id=app_id)
        elif 'app' in args_dict and 'cloud' in args_dict:

            app_data = args['app']
            cloud_data = args['cloud']
            task_name = app_name = app_data['app_name']
            app_tar_name = app_data['app_tar_name']
            content = app_data['app_content']
            cloud = cloud_data['type']

            app_location, app_version = self._store_app_contents(app_name, app_tar_name, content)

            app_data['app_location'] = app_location
            app_data['app_version'] = app_version
            task_def = task_definition.TaskDefinition(app_data, cloud_data, '')

            app_id = utils.get_id(APP_STORE_PATH, "app_ids.txt", app_name, app_version, '', '', cloud)
            logging.debug("App id:%s" % app_id)
            response.headers['location'] = ('/deployments/{app_id}').format(app_id=app_id)

        # dispatch the handler thread
        delegatethread = mgr.Manager(task_name, task_def)
        thread.start_new_thread(start_thread, (delegatethread, ))
        logging.debug("Location header:%s" % response.headers['location'])
        logging.debug("Response:%s" % response)

        return response

api.add_resource(Cloud, '/clouds/<cloud_name>')
api.add_resource(App, '/apps/<app_name>')
api.add_resource(Service, '/services/<service_name>')
api.add_resource(ServiceGetDeployID, '/servicesdepshow/<dep_id>')
api.add_resource(Deployment, '/deployments/<dep_id>')
api.add_resource(Deployments, '/deployments')

if __name__ == '__main__':
    # Create the data directory if it does not exist

    logging.basicConfig(filename="lme.log", level=logging.DEBUG, filemode='a')
    logging.basicConfig(format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')
    if not os.path.exists(APP_STORE_PATH):
        os.makedirs(APP_STORE_PATH)
    logging.info("Starting lme server")
    app.run(debug=True, threaded=True, host='0.0.0.0', port=5002)