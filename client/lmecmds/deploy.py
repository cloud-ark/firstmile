import logging
import prettytable
import os
import subprocess
import yaml
import sys

import common
import deployment as dp

from os.path import expanduser

from cliff.command import Command

home_dir = expanduser("~")

APP_STORE_PATH = ("{home_dir}/.lme/data/deployments").format(home_dir=home_dir)


class Deploy(Command):
    "Build and deploy application"

    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)

    def get_parser(self, prog_name):
        parser = super(Deploy, self).get_parser(prog_name)
        #parser.add_argument('filename', nargs='?', default='.')
        parser.add_argument('--service',
                            dest='service',
                            help="Name of the required service (e.g.: MySQL)")
        parser.add_argument('--cloud',
                            dest='cloud',
                            help="Destination to deploy application (local, AWS, Google)")        
        return parser

    def _setup_aws(self, dest):
        aws_creds_path = APP_STORE_PATH + "/aws-creds"
        if not os.path.exists(aws_creds_path):
            os.makedirs(aws_creds_path)
            access_key_id = raw_input("Enter AWS Access Key:")
            secret_access_key = raw_input("Enter AWS Secret Access Key:")
            fp = open(aws_creds_path + "/credentials", "w")
            fp.write("[default]\n")
            fp.write("aws_access_key_id = %s\n" % access_key_id)
            fp.write("aws_secret_access_key = %s\n" % secret_access_key)
            fp.close()

            fp = open(aws_creds_path + "/config", "w")
            fp.write("[default]\n")
            fp.write("output = json\n")
            fp.write("region = us-west-2\n")
            fp.close()

    def _get_google_project_user_details(self, project_location):
        google_app_details_path = APP_STORE_PATH + "/google-creds/app_details.txt"
        app_name = project_location[project_location.rfind("/")+1:]
        project_id = ''
        user_email = ''
        if os.path.exists(google_app_details_path):
            fp = open(google_app_details_path, "r")
            lines = fp.readlines()
            for line in lines:
                parts = line.split(":")
                potential_project_id = parts[1].rstrip().lstrip()
                if line.find("User Email") >=0:
                    user_email = parts[1].rstrip().lstrip()
                if potential_project_id.find(app_name) >= 0:
                    project_id = potential_project_id
            if not user_email:
                user_email = raw_input("Enter Gmail address associated with your Google App Engine account>")
                fp = open(google_app_details_path, "a")
                fp.write("User Email:%s\n" % user_email)
                fp.close()
            if not project_id:
                project_id = raw_input("Enter project id>")
                fp = open(google_app_details_path, "a")
                fp.write("Project ID:%s\n" % project_id)
                fp.close()
        else:
            project_id = raw_input("Enter project id>")
            user_email = raw_input("Enter Gmail address associated with your Google App Engine account>")
            fp = open(google_app_details_path, "w")
            fp.write("User Email:%s\n" % user_email)
            fp.write("Project ID:%s\n" % project_id)
            fp.close()
        return project_id, user_email

    def _setup_google(self, project_location, dest):
        google_creds_path = APP_STORE_PATH + "/google-creds"
        if not os.path.exists(google_creds_path):
            os.makedirs(google_creds_path)

            df = ("FROM ubuntu:14.04 \n"
                  "RUN apt-get update && apt-get install -y wget python \n"
                  "RUN sudo wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-126.0.0-linux-x86_64.tar.gz && \ \n"
                  "    sudo gunzip google-cloud-sdk-126.0.0-linux-x86_64.tar.gz && \ \n"
                  "    sudo tar -xvf google-cloud-sdk-126.0.0-linux-x86_64.tar \n"
                  "RUN /google-cloud-sdk/bin/gcloud components install beta \n"
                  "ENTRYPOINT [\"/google-cloud-sdk/bin/gcloud\", \"beta\", \"auth\", \"login\", \"--no-launch-browser\"] \n")

            docker_file = open(google_creds_path + "/Dockerfile", "w")
            docker_file.write(df)
            docker_file.close()

            app_name = cwd = os.getcwd()
            os.chdir(google_creds_path)
            k = app_name.rfind("/")
            app_name = app_name[k+1:]

            docker_build_cmd = ("docker build -t {app_name}_creds .").format(app_name=app_name)
            os.system(docker_build_cmd)

            docker_run_cmd = ("docker run -i -t {app_name}_creds").format(app_name=app_name)
            os.system(docker_run_cmd)

            cont_id_cmd = ("docker ps -a | grep {app_name}_creds | cut -d ' ' -f 1 | head -1").format(app_name=app_name)
            #print("Copy command:%s" % cont_id_cmd)
            cont_id = subprocess.check_output(cont_id_cmd, shell=True).rstrip().lstrip()

            #print("Container ID:%s" % cont_id)

            copy_file_cmd = ("docker cp {cont_id}:/root/.config/gcloud {google_creds_path}").format(cont_id=cont_id,
                                                                                                     google_creds_path=google_creds_path)
            #print("Copy command:%s" % copy_file_cmd)
            os.system(copy_file_cmd)

            os.chdir(cwd)

    def _get_app_details(self):
        app_port = '5000'
        app_type = 'python'

        default_entry_point = "application.py"
        entry_point = raw_input("Enter file name that has main function in it (e.g.: application.py)>")
        if not entry_point:
            entry_point = default_entry_point

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
        self.log.info('Deploying application')
        self.log.debug('Deploying application. Passed args:%s' % parsed_args)

        project_location = os.getcwd()
        self.log.debug("App directory:%s" % project_location)

        app_info = common.read_app_info()
        if not app_info:
            app_info = self._get_app_details()

        service = parsed_args.service
        dest = parsed_args.cloud

        service_info = common.read_service_info()

        if not service_info:
            if service:
                self.log.debug("Service:%s" % service)
                service_info = self._get_service_details(service)
                app_info = self._get_app_service_details(app_info)

        cloud_info = common.read_cloud_info()
        if not cloud_info:
            if dest:
                self.log.debug("Destination:%s" % dest)
                if dest.lower() == 'aws':
                    self._setup_aws(dest)
                    cloud_info['type'] = 'aws'
                if dest.lower() == 'google':
                    project_id = ''
                    user_email = ''
                    self._setup_google(project_location, dest)
                    project_id, user_email = self._get_google_project_user_details(project_location)
                    print("Using project_id:%s" % project_id)
                    print("Using user email:%s" % user_email)
                    cloud_info['type'] = 'google'
                    cloud_info['project_id'] = project_id
                    cloud_info['user_email'] = user_email
                if dest.lower() == 'local':
                    cloud_info['type'] = 'local'
                    cloud_info['app_port'] = '5000'
            else:
                print("Cloud deployment target not specified. Exiting.")
                sys.exit(0)

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



            

