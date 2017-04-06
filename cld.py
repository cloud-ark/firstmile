'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com>
'''

import datetime
import logging
import os
import sys
import tarfile
import time
import thread

from os.path import expanduser

from flask import Flask, jsonify, request
from flask_restful import reqparse, abort, Resource, Api

from manager import manager as mgr
from common import task_definition
from common import utils
from common import service
from common import constants
from common import fm_logger


app = Flask(__name__)
api = Api(app)

parser = reqparse.RequestParser()
parser.add_argument('app_content', location='form')
parser.add_argument('app_name', location='form')

home_dir = expanduser("~")

APP_STORE_PATH = ("{home_dir}/.cld/data/deployments").format(home_dir=home_dir)
SERVICE_STORE_PATH = APP_STORE_PATH + "/services"


def exception_handler(exctype, value, traceback):
    fmlogging.error("Exception:" % exctype)
    fmlogging.error("-----")
    fmlogging.error(value)
    fmlogging.error("-----")
    fmlogging.error(traceback)

sys.excepthook = exception_handler

def start_thread(delegatethread):
    try:
        delegatethread.run()
    except Exception as e:
        fmlogging.error(e)
        delegatethread.error_update()

class Cloud(Resource):

    def _get(self, cloud_name):
        app_lines = list()
        f = open(APP_STORE_PATH + "/app_ids.txt")
        all_lines = f.readlines()
        for line in all_lines:
            line_contents = line.split(" ")
            app_line = {}

            if line_contents[0] != 'deleted':
                app_version = line_contents[1]
                k = app_version.find("--")
                app_name = app_version[:k]
                app_version = app_version[k+2:].rstrip().lstrip()
                if len(line_contents) >= 3:
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
        fmlogging.debug("Executing GET for cloud:%s" % cloud_name)
        app_lines = list()

        if os.path.exists(APP_STORE_PATH + "/app_ids.txt"):
            app_lines = self._get(cloud_name)

        resp_data = {}

        resp_data['app_data'] = app_lines

        response = jsonify(**resp_data)
        response.status_code = 200
        return response

class Services(Resource):
    def get(self):
        fmlogging.debug("Executing GET for all services")

        status_lines = utils.read_statues(SERVICE_STORE_PATH, "service_ids.txt",
                                          "service-status.txt", '', '')
        resp_data = {}

        resp_data['data'] = status_lines

        response = jsonify(**resp_data)
        response.status_code = 200
        return response

class Service(Resource):
    def get(self, service_name):
        fmlogging.debug("Executing GET for service:%s" % service_name)

        status_lines = utils.read_statues(SERVICE_STORE_PATH, "service_ids.txt", 
                                          "service-status.txt", service_name, '')
        status_and_details_lines = utils.read_service_details(SERVICE_STORE_PATH, "service_ids.txt",
                                                              "service-details.txt", service_name, '', status_lines)

        resp_data = {}

        resp_data['data'] = status_and_details_lines

        response = jsonify(**resp_data)
        response.status_code = 200
        return response

class ServiceDeployID(Resource):

    def _update_service_status(self, info):
        service_name = info['service_name']
        service_version = info['service_version']
        app_status_file = (SERVICE_STORE_PATH + "/{service_name}/{service_version}/service-status.txt").format(service_name=service_name,
                                                                                                               service_version=service_version)
        fp = open(app_status_file, "a")
        status_line = (", status::{status}").format(status=constants.DELETING)
        fp.write(status_line)
        fp.flush()
        fp.close()

    def get(self, dep_id):
        fmlogging.debug("Executing GET for deploy id:%s" % dep_id)

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
        response.status_code = 200
        return response

    def delete(self, dep_id):
        fmlogging.debug("Executing DELETE for dep id:%s" % dep_id)
        info = utils.get_service_info(SERVICE_STORE_PATH, "service_ids.txt", dep_id)

        resp_data = {}
        response = jsonify(**resp_data)

        cloud_data = {}
        if info:
            cloud_data['type'] = info['cloud']
            task_def = task_definition.TaskDefinition('', cloud_data, '')

            # update service status to DELETING
            self._update_service_status(info)

            # dispatch the handler thread
            delegatethread = mgr.Manager(task_def=task_def, delete_action=True, delete_info=info)
            thread.start_new_thread(start_thread, (delegatethread, ))

            response.status_code = 202
        else:
            response.status_code = 404
        return response

class App(Resource):
    def get(self, app_name):
        fmlogging.debug("Executing GET for app:%s" % app_name)

        status_lines = utils.read_statues(APP_STORE_PATH, "app_ids.txt",
                                          "app-status.txt", app_name, '')
        resp_data = {}
        response = jsonify(**resp_data)

        if status_lines:
            resp_data['data'] = status_lines
            response = jsonify(**resp_data)
            response.status_code = 200
        else:
            response.status_code = 404
        return response

class Apps(Resource):

    def get(self):
        fmlogging.debug("Executing GET for all apps")

        status_lines = utils.read_statues(APP_STORE_PATH, "app_ids.txt",
                                          "app-status.txt", '', '')
        resp_data = {}

        resp_data['data'] = status_lines

        response = jsonify(**resp_data)
        response.status_code = 200
        return response

class Logs(Resource):

    def get(self, dep_id):
        fmlogging.debug("Executing GET for app:%s" % dep_id)

        info = utils.get_app_and_service_info(APP_STORE_PATH, "app_ids.txt", dep_id)

        app_exists = False
        if info:
            status_data = {}
            status_data['name'] = info['app_name']
            status_data['version'] = info['app_version']
            status_data['cloud'] = info['cloud']

            if os.path.exists(constants.APP_STORE_PATH + "/" + info['app_name'] + "/" + info['app_version']):
                app_exists = True
                dep_log_file_name = info['app_version'] + constants.DEPLOY_LOG

                prefix = os.getenv('HOST_HOME')
                fmlogging.debug("HOST_HOME: %s" % prefix)
                fmlogging.debug("Inside get_logs - prefix value for log file path:%s" % prefix)
                if not prefix:
                    prefix = constants.APP_STORE_PATH
                    fmlogging.debug("Inside get_logs - prefix value for log file path:%s" % prefix)
                dep_log_file = prefix + "/" + info['app_name'] + "/"
                dep_log_file = dep_log_file + info['app_version'] + "/" + dep_log_file_name
                if prefix == constants.APP_STORE_PATH:
                    if not os.path.exists(dep_log_file):
                        dep_log_file = ""
                status_data['dep_log_location'] = dep_log_file

                # Get runtime log
                cloud_data = {}
                cloud_data['type'] = info['cloud']
                task_def = task_definition.TaskDefinition('', cloud_data, '')
                mgr.Manager(task_def=task_def).get_logs(info)

                app_log_file_name = info['app_version'] + constants.RUNTIME_LOG
                app_log_file = prefix + "/" + info['app_name'] + "/"
                app_log_file = app_log_file + info['app_version'] + "/" + app_log_file_name
                if prefix == constants.APP_STORE_PATH:
                    if not os.path.exists(app_log_file):
                        app_log_file = ""
                status_data['run_log_location'] = app_log_file

                resp_data = {}
                resp_data['data'] = status_data
                response = jsonify(**resp_data)
                response.status_code = 200

        if not app_exists:
            resp_data = {}
            response = jsonify(**resp_data)
            response.status_code = 404
        return response

class Deployment(Resource):
    def _update_app_status(self, info):
        app_name = info['app_name']
        app_version = info['app_version']
        app_status_file = (APP_STORE_PATH + "/{app_name}/{app_version}/app-status.txt").format(app_name=app_name,
                                                                                               app_version=app_version)
        fp = open(app_status_file, "a")
        status_line = (", status::{status}").format(status=constants.DELETING)
        fp.write(status_line)
        fp.flush()
        fp.close()

    def delete(self, dep_id):
        fmlogging.debug("Executing DELETE for dep id:%s" % dep_id)
        info = utils.get_app_and_service_info(APP_STORE_PATH, "app_ids.txt", dep_id)

        resp_data = {}
        response = jsonify(**resp_data)

        cloud_data = {}
        if info:
            cloud_data['type'] = info['cloud']
            task_def = task_definition.TaskDefinition('', cloud_data, '')

            # update app status to DELETING
            self._update_app_status(info)

            # dispatch the handler thread
            delegatethread = mgr.Manager(task_def=task_def, delete_action=True, delete_info=info)
            thread.start_new_thread(start_thread, (delegatethread, ))

            response.status_code = 202
        else:
            response.status_code = 404
        return response

    def get(self, dep_id):
        fmlogging.debug("Executing GET for dep id:%s" % dep_id)
        status_data = utils.read_statuses_given_id(APP_STORE_PATH,
                                                   "app_ids.txt",
                                                   "app-status.txt",
                                                   dep_id)
        resp_data = {}
        response = jsonify(**resp_data)

        if status_data:
            resp_data['data'] = status_data
            response = jsonify(**resp_data)
            response.status_code = 200
        else:
            response.status_code = 404
        return response

    def get_1(self, dep_id):
        fmlogging.debug("Executing GET for dep id:%s" % dep_id)

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
            fmlogging.debug("App version:%s" % app_version)

            dep_id = dep_id[:k]
            l = dep_id.rfind("/")
            app_name = dep_id[l+1:]
            fmlogging.debug("App name:%s" % app_name)
            return APP_STORE_PATH + "/" + app_name + "/" + app_version

        app_location = _get_app_location(dep_id)
        fmlogging.debug("App location:%s" % app_location)

        try:
            app_status_data = "No status available yet."
            status_file = app_location + "/app-status.txt"
            app_status_file = open(status_file, "r")
            app_status_data = app_status_file.read()
            fmlogging.debug("--- App status ---")
            fmlogging.debug(app_status_data)
            fmlogging.debug("--- App status ---")
        except IOError:
            fmlogging.error("Status file does not exist:%s" % str(status_file))
            fmlogging.error("App status: %s" % app_status_data)
        
        resp_data = {}
        resp_data['app_data'] = app_status_data

        response = jsonify(**resp_data)
        response.status_code = 200
        return response

class Deployments(Resource):
    def _untar_the_app(self, app_tar_file, versioned_app_path):
        #TODO(devkulkarni): Untaring is not working

        fmlogging.debug("Untarring received app tar file %s" % app_tar_file)
        os.chdir(versioned_app_path)
        tar = tarfile.open(app_tar_file)
        tar.extractall(path=versioned_app_path)
        tar.close()
        #for member in tar.getmembers():
        #    tar.extractfile(member)
        #tar.close()

        #untar_cmd = ("tar -xf {app_tar_file} -C {versioned_app_path}").format(app_tar_file=app_tar_file,
        #                                                                       versioned_app_path=versioned_app_path)
        #result = subprocess.check_output(untar_cmd, shell=True)
        #logging.debug(result)

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
        service_data[0]['service_name'] = service_name
        return service_data, service_version

    # Handle service, app, and app+service deployments
    def post(self):
        #args = parser.parse_args()
        fmlogging.debug("Received POST request.")
        args = request.get_json(force=True)
        
        response = jsonify()
        response.status_code = 201

        args_dict = dict(args)

        try:
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
                                      service_version, '', '', '', cloud, cloud_data)
                fmlogging.debug("Service id:%s" % service_id)
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

                service_name = service.Service(service_data[0]).get_service_type() + "-" + app_name
                service_data, service_version = self._update_service_data(service_data,
                                                                          service_name,
                                                                          app_version)
                task_def = task_definition.TaskDefinition(app_data, cloud_data, service_data)

                service_id = utils.get_id(SERVICE_STORE_PATH, "service_ids.txt", service_name,
                                      service_version, '', '', '', cloud, cloud_data)
                fmlogging.debug("Service id:%s" % service_id)

                app_id = utils.get_id(APP_STORE_PATH, "app_ids.txt", app_name, app_version,
                                      service_name, service_version, service_id, cloud, cloud_data)
                fmlogging.debug("App id:%s" % app_id)
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

                app_id = utils.get_id(APP_STORE_PATH, "app_ids.txt", app_name, app_version,
                                      '', '', '', cloud, cloud_data)
                fmlogging.debug("App id:%s" % app_id)
                response.headers['location'] = ('/deployments/{app_id}').format(app_id=app_id)

            # dispatch the handler thread
            delegatethread = mgr.Manager(task_name, task_def)
            thread.start_new_thread(start_thread, (delegatethread, ))
            fmlogging.debug("Location header:%s" % response.headers['location'])
            fmlogging.debug("Response:%s" % response)
        except OSError as oe:
            fmlogging.error(oe)
            # Send back service unavailable status
            response.status_code = 503

        return response

api.add_resource(Cloud, '/clouds/<cloud_name>')
api.add_resource(Apps, '/apps')
api.add_resource(App, '/apps/<app_name>')
api.add_resource(Services, '/services')
api.add_resource(Service, '/services/<service_name>')
api.add_resource(ServiceDeployID, '/servicesdep/<dep_id>')
api.add_resource(Deployment, '/deployments/<dep_id>')
api.add_resource(Deployments, '/deployments')
api.add_resource(Logs, '/logs/<dep_id>')

if __name__ == '__main__':
    #logging.basicConfig(filename=constants.LOG_FILE_NAME,
    #                    level=logging.DEBUG, filemode='a')
    #logging.basicConfig(format='%(asctime)s %(message)s',
    #                    datefmt='%m/%d/%Y %I:%M:%S %p')
    # Create the data directory if it does not exist
    if not os.path.exists(APP_STORE_PATH):
        os.makedirs(APP_STORE_PATH)
    #logging.info("Starting lme server")
    fmlogging = fm_logger.Logging()
    fmlogging.info("Starting LME server")

    from gevent.wsgi import WSGIServer
    http_server = WSGIServer(('', 5002), app)
    http_server.serve_forever()

    #app.run(debug=True, threaded=True, host='0.0.0.0', port=5002)