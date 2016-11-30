import logging
import os

import deployment as dp

from cliff.command import Command


class Deploy(Command):
    "Build and deploy application"

    log = logging.getLogger(__name__)

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
        self.log.info('deploying application')
        self.log.debug('debugging')
        self.app.stdout.write('deploying application!\n')

        #self.app.stdout.write('File name:%s' % parsed_args.filename)
        #self.app.stdout.write("Passed args:%s" % parsed_args)
        service = parsed_args.service
        if service:
            self.log.info("Service:%s" % service)
        
        dest = parsed_args.cloud
        if dest:
            self.log.info("Destination:%s" % dest)
            
        app_port = '5000'
        
        # We need to figure out application details
        app_info = {}
        app_info['app_type'] = 'python'
        app_info['entrypoint'] = 'application.py'
            
        service_info = {}
        service_info['service_name'] = 'mysql-service'
        service_info['service_type'] = 'mysql'

        project_location = os.getcwd()
        self.log.info("App directory:%s" % project_location)
        
        self.dep_track_url = dp.Deployment().post(project_location, app_info, 
                                                  service_info, cloud='local')
        print("App tracking url:%s" % self.dep_track_url)

            

