import logging
import prettytable
import os
import subprocess


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

            print("Container ID:%s" % cont_id)

            copy_file_cmd = ("docker cp {cont_id}:/root/.config/gcloud {google_creds_path}").format(cont_id=cont_id,
                                                                                                     google_creds_path=google_creds_path)
            print("Copy command:%s" % copy_file_cmd)
            os.system(copy_file_cmd)

            os.chdir(cwd)

    def _get_app_details(self):
        cwd = os.getcwd()
        lmefile = cwd + "/lme.yml"
        app_port = '5000'
        entry_point = ''
        fp = open(lmefile, "a+")
        if os.path.exists(lmefile):
            lines = fp.readlines()
            for line in lines:
                parts = line.split(":")
                if line.find("entry_point") >= 0:
                    entry_point = parts[1].rstrip().lstrip()
                if line.find("port") >=0:
                    app_port = parts[1].rstrip().lstrip()

        if not entry_point:
            entry_point = "application.py"
            entry_point = raw_input("Enter file name that has main function in it (e.g.: application.py)>")
            fp.write("entry_point:%s\n" % entry_point)
            fp.write("app_port:5000\n")
            fp.close()

        return app_port, entry_point

    def _get_service_details(self, service_info):
        cwd = os.getcwd()
        lmefile = cwd + "/lme.yml"
        db_var = host_var = user_var = password_var = db_name = ''
        fp = open(lmefile, "a+")
        if os.path.exists(lmefile):
            lines = fp.readlines()
            for line in lines:
                parts = line.split(":")
                if line.find("db_var") >= 0:
                    db_var = parts[1].rstrip().lstrip()
                if line.find("host_var") >= 0:
                    host_var = parts[1].rstrip().lstrip()
                if line.find("user_var") >= 0:
                    user_var = parts[1].rstrip().lstrip()
                if line.find("password_var") >= 0:
                    password_var = parts[1].rstrip().lstrip()
                if line.find("db_name") >= 0:
                    db_name = parts[1].rstrip().lstrip()

        if not db_var:
            db_var = raw_input("Enter name of variable in your app used to reference the database>")
            fp.write("db_var:%s\n" % db_var)
        if not host_var:
            host_var = raw_input("Enter name of variable in your app used to reference the db server/host>")
            fp.write("host_var:%s\n" % host_var)
        if not user_var:
            user_var = raw_input("Enter name of variable in your app used to reference the db user>")
            fp.write("user_var:%s\n" % user_var)
        if not password_var:
            password_var = raw_input("Enter name of variable in your app used to reference the db password>")
            fp.write("password_var:%s\n" % password_var)
        if not db_name:
            db_name = raw_input("Enter name for the database. LME will create this database on target cloud.>")
            fp.write("db_name:%s\n" % db_name)

        fp.close()

        service_info["db_var"] = db_var
        service_info["host_var"] = host_var
        service_info["user_var"] = user_var
        service_info["password_var"] = password_var
        service_info["db_name"] = db_name

        return service_info

    def take_action(self, parsed_args):
        self.log.info('Deploying application')
        self.log.debug('Deploying application. Passed args:%s' % parsed_args)

        project_location = os.getcwd()
        self.log.debug("App directory:%s" % project_location)

        service = parsed_args.service
        if service:
            self.log.debug("Service:%s" % service)
        
        dest = parsed_args.cloud
        project_id = ''
        user_email = ''
        if dest:
            self.log.debug("Destination:%s" % dest)
            if dest.lower() == 'aws':
                self._setup_aws(dest)
            if dest.lower() == 'google':
                self._setup_google(project_location, dest)
                project_id, user_email = self._get_google_project_user_details(project_location)
                print("Using project_id:%s" % project_id)
                print("Using user email:%s" % user_email)

        app_port, entry_point = self._get_app_details()
        
        # We need to figure out application details
        app_info = {}
        app_info['app_port'] = app_port
        app_info['app_type'] = 'python'
        app_info['entry_point'] = entry_point
        app_info['project_id'] = project_id
        app_info['user_email'] = user_email
            
        service_info = {}
        if service:
            if service.lower() == 'mysql':
                service_info['service_name'] = 'mysql-service'
                service_info['service_type'] = 'mysql'
                service_info = self._get_service_details(service_info)
            else:
                print("Service %s not supported. Supported services are: mysql" % service)
                exit(0)

        self.dep_track_url = dp.Deployment().post(project_location, app_info, 
                                                  service_info, cloud=dest)
        self.log.debug("App tracking url:%s" % self.dep_track_url)

        k = project_location.rfind("/")
        app_name = project_location[k+1:]

        l = self.dep_track_url.rfind("/")
        dep_id = self.dep_track_url[l+1:]

        x = prettytable.PrettyTable()
        x.field_names = ["App Name", "Deploy ID", "Cloud"]

        x.add_row([app_name, dep_id, dest])
        self.app.stdout.write("%s\n" % x)
        self.log.debug(x)



            

