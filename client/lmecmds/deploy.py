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

    def _setup_google(self, dest):
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

    def take_action(self, parsed_args):
        self.log.info('Deploying application')
        self.log.debug('Deploying application. Passed args:%s' % parsed_args)

        service = parsed_args.service
        if service:
            self.log.debug("Service:%s" % service)
        
        dest = parsed_args.cloud
        if dest:
            self.log.debug("Destination:%s" % dest)
            if dest.lower() == 'aws':
                self._setup_aws(dest)
            if dest.lower() == 'google':
                self._setup_google(dest)
            
        app_port = '5000'
        
        # We need to figure out application details
        app_info = {}
        app_info['app_type'] = 'python'
        app_info['entrypoint'] = 'application.py'
            
        service_info = {}
        if service and service.lower() == 'mysql':
            service_info['service_name'] = 'mysql-service'
            service_info['service_type'] = 'mysql'

        project_location = os.getcwd()
        self.log.debug("App directory:%s" % project_location)
        
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



            

