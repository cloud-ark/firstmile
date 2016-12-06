import logging
import os
import prettytable

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



            

