import logging
import os
import prettytable

import deployment as dp

from cliff.command import Command


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

    def take_action(self, parsed_args):
        self.log.info('Deploying application')
        self.log.debug('Deploying application. Passed args:%s' % parsed_args)

        service = parsed_args.service
        if service:
            self.log.debug("Service:%s" % service)
        
        dest = parsed_args.cloud
        if dest:
            self.log.debug("Destination:%s" % dest)
            
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
                                                  service_info, cloud='local')
        self.log.debug("App tracking url:%s" % self.dep_track_url)

        k = project_location.rfind("/")
        app_name = project_location[k+1:]

        l = self.dep_track_url.rfind("/")
        dep_id = self.dep_track_url[l+1:]

        x = prettytable.PrettyTable()
        x.field_names = ["App Name", "Deploy ID"]

        x.add_row([app_name, dep_id])
        self.app.stdout.write("%s\n" % x)
        self.log.debug(x)



            

