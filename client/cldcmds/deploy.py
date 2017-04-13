'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com>
'''

import logging
import prettytable
import os
import sys

import common
import deployment as dp

from cliff.command import Command


class Deploy(Command):
    "Build and deploy an application"

    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)

    def get_parser(self, prog_name):
        parser = super(Deploy, self).get_parser(prog_name)
        parser.add_argument('--service',
                            dest='service',
                            help="Name of the required service (E.g.: mysql)")
        parser.add_argument('--cloud',
                            dest='cloud',
                            help="Destination to deploy application (local-docker, aws, google)")        
        return parser

    def _check_entry_point(self, entry_point):
        valid = False
        if not os.path.exists("./" + entry_point):
            return valid
        if os.path.isdir(entry_point):
            return valid

        fp = open(entry_point, "r")
        lines = fp.readlines()
        check_1 = False
        check_2 = False
        for line in lines:
            line = line.replace("\"",'')
            line = line.replace("'",'')
            line = line.replace("\s+","\s")
            if line.find("Flask(__name__)") >= 0:
                check_1 = True
            if line.find("__main__") >= 0:
                check_2 = True
        valid = check_1 and check_2
        return valid

    def _check_port(self, port):
        try:
            int(port)
            return True
        except ValueError:
            return False

    def _get_app_details(self):
        default_app_port = common.DEFAULT_APP_PORT
        app_type = common.DEFAULT_APP_TYPE

        default_entry_point = "application.py"

        valid_entry_point = False
        while not valid_entry_point:
            entry_point = raw_input("Enter application's main file (default: application.py)>")
            if not entry_point:
                entry_point = default_entry_point
            valid_entry_point = self._check_entry_point(entry_point)

        valid_port = False
        while not valid_port:
            app_port = raw_input("Enter port number on which application listens (default: 5000>)")
            if not app_port:
                app_port = default_app_port
            valid_port = self._check_port(app_port)

        app_info = {}
        app_info['entry_point'] = entry_point
        app_info['app_port'] = app_port
        app_info['app_type'] = app_type
        return app_info

    def _get_service_details(self, service):
        service_details = {}
        service_list = []
        service_details['type'] = service

        service_info = {}
        service_info['service'] = service_details
        service_list.append(service_info)
        return service_list

    def _get_app_service_details(self, app_info):
        db_var = raw_input("Enter name of variable in your app used to reference the database>")
        host_var = raw_input("Enter name of variable in your app used to reference the db server/host>")
        user_var = raw_input("Enter name of variable in your app used to reference the db user>")
        password_var = raw_input("Enter name of variable in your app used to reference the db password>")

        service_info = {}
        service_info["db_var"] = db_var
        service_info["host_var"] = host_var
        service_info["user_var"] = user_var
        service_info["password_var"] = password_var
        app_info['app_variables'] = service_info
        return app_info

    def take_action(self, parsed_args):
        self.log.debug('Deploying application. Passed args:%s' % parsed_args)

        service = parsed_args.service
        dest = parsed_args.cloud
        common.verify_inputs(service, dest)

        project_location = os.getcwd()
        self.log.debug("App directory:%s" % project_location)

        cloud_info = common.read_cloud_info()
        if not cloud_info:
            if dest:
                self.log.debug("Destination:%s" % dest)
            else:
                dest = raw_input("Please enter Cloud deployment target>")
                common.verify_inputs(service, dest)
            if dest.lower() == common.AWS:
                common.setup_aws()
                cloud_info['type'] = common.AWS
            if dest.lower() == common.GOOGLE:
                project_id = ''
                user_email = ''
                common.setup_google()
                project_id, user_email = common.get_google_project_user_details(project_location)
                cloud_info['type'] = common.GOOGLE
                cloud_info['project_id'] = project_id
                cloud_info['user_email'] = user_email
            if dest.lower() == common.LOCAL_DOCKER:
                cloud_info['type'] = common.LOCAL_DOCKER
                cloud_info['app_port'] = '5000'
        else:
            if dest and cloud_info['type'] != dest:
                print("Looks like there is cld.yaml present in the directory and the value of the cloud flag differs between command line and cld.yaml.")
                print("Using values in cld.yaml.")

        app_info = common.read_app_info()
        if not app_info:
            app_info = self._get_app_details()

        service_info = common.read_service_info()

        if not service_info:
            if service:
                self.log.debug("Service:%s" % service)
                service_info = self._get_service_details(service)
                app_info = self._get_app_service_details(app_info)


        self.dep_track_url = dp.Deployment().post(project_location, app_info, 
                                                  service_info, cloud_info)
        self.log.debug("App tracking url:%s" % self.dep_track_url)

        k = project_location.rfind("/")
        app_name = project_location[k+1:]

        l = self.dep_track_url.rfind("/")
        dep_id = self.dep_track_url[l+1:]

        x = prettytable.PrettyTable()
        x.field_names = ["App Name", "Deploy ID", "Cloud"]

        x.add_row([app_name, dep_id, cloud_info['type']])
        self.app.stdout.write("%s\n" % x)
        self.log.debug(x)